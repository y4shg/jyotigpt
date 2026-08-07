"""Retrieval engine.

The document-processing and search machinery behind the retrieval HTTP
surface: loading documents from files/URLs/youtube, chunking and
embedding them into the vector store, web search across the configured
engines, and the batch file processor shared with the knowledge domain.

Everything here works against ``request.app.state`` so the same engine
serves the admin config endpoints and the per-user processing flows.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, Request, status
from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document
import tiktoken

from jyotigpt.config import (
    DEFAULT_LOCALE,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
)
from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import DEVICE_TYPE, DOCKER, SRC_LOG_LEVELS
from jyotigpt.models.files import FileModel, Files
from jyotigpt.retrieval.loaders.main import Loader
from jyotigpt.retrieval.loaders.youtube import YoutubeLoader
from jyotigpt.retrieval.utils import (
    get_embedding_function,
    get_model_path,
)
from jyotigpt.retrieval.vector.connector import VECTOR_DB_CLIENT
from jyotigpt.retrieval.web.bing import search_bing
from jyotigpt.retrieval.web.bocha import search_bocha
from jyotigpt.retrieval.web.brave import search_brave
from jyotigpt.retrieval.web.duckduckgo import search_duckduckgo
from jyotigpt.retrieval.web.exa import search_exa
from jyotigpt.retrieval.web.google_pse import search_google_pse
from jyotigpt.retrieval.web.jina_search import search_jina
from jyotigpt.retrieval.web.kagi import search_kagi
from jyotigpt.retrieval.web.main import SearchResult
from jyotigpt.retrieval.web.mojeek import search_mojeek
from jyotigpt.retrieval.web.perplexity import search_perplexity
from jyotigpt.retrieval.web.searchapi import search_searchapi
from jyotigpt.retrieval.web.searxng import search_searxng
from jyotigpt.retrieval.web.serpapi import search_serpapi
from jyotigpt.retrieval.web.serper import search_serper
from jyotigpt.retrieval.web.serply import search_serply
from jyotigpt.retrieval.web.serpstack import search_serpstack
from jyotigpt.retrieval.web.sougou import search_sougou
from jyotigpt.retrieval.web.tavily import search_tavily
from jyotigpt.retrieval.web.utils import get_web_loader
from jyotigpt.storage.provider import Storage
from jyotigpt.utils.misc import calculate_sha256_string

from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


########################################
# Embedding / reranking model loaders
########################################


def get_ef(
    engine: str,
    embedding_model: str,
    auto_update: bool = False,
):
    """Load the local embedding model for ``engine == ""``, else None.

    ``auto_update`` only matters for the local-sentence-transformer path;
    remote embedding engines never go through here.
    """
    ef = None
    if embedding_model and engine == "":
        from sentence_transformers import SentenceTransformer

        try:
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
            )
        except Exception as e:
            log.debug(f"Error loading SentenceTransformer: {e}")

    return ef


def get_rf(
    reranking_model: Optional[str] = None,
    auto_update: bool = False,
):
    """Load the reranking model, either the ColBERT wrapper or a CrossEncoder."""
    rf = None
    if reranking_model:
        if any(model in reranking_model for model in ["jinaai/jina-colbert-v2"]):
            try:
                from jyotigpt.retrieval.models.colbert import ColBERT

                rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env="docker" if DOCKER else None,
                )

            except Exception as e:
                log.error(f"ColBERT: {e}")
                raise Exception(ERROR_MESSAGES.DEFAULT(e))
        else:
            import sentence_transformers

            try:
                rf = sentence_transformers.CrossEncoder(
                    get_model_path(reranking_model, auto_update),
                    device=DEVICE_TYPE,
                    trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                )
            except Exception as e:
                log.error(f"CrossEncoder: {e}")
                raise Exception(ERROR_MESSAGES.DEFAULT("CrossEncoder error"))
    return rf


def embedding_function_for(request: Request, user=None):
    """Resolve the configured embedding callable from the app state."""
    config = request.app.state.config
    return get_embedding_function(
        config.RAG_EMBEDDING_ENGINE,
        config.RAG_EMBEDDING_MODEL,
        request.app.state.ef,
        (
            config.RAG_OPENAI_API_BASE_URL
            if config.RAG_EMBEDDING_ENGINE == "openai"
            else config.RAG_OLLAMA_BASE_URL
        ),
        (
            config.RAG_OPENAI_API_KEY
            if config.RAG_EMBEDDING_ENGINE == "openai"
            else config.RAG_OLLAMA_API_KEY
        ),
        config.RAG_EMBEDDING_BATCH_SIZE,
    )


########################################
# Vector store writes
########################################


def _get_docs_info(docs: list[Document]) -> str:
    """Join the identifying names of ``docs`` for log messages."""
    docs_info = set()

    # Trying to select relevant metadata identifying the document.
    for doc in docs:
        metadata = getattr(doc, "metadata", {})
        doc_name = metadata.get("name", "")
        if not doc_name:
            doc_name = metadata.get("title", "")
        if not doc_name:
            doc_name = metadata.get("source", "")
        if doc_name:
            docs_info.add(doc_name)

    return ", ".join(docs_info)


def _text_splitter_for(config) -> RecursiveCharacterTextSplitter | TokenTextSplitter:
    """Build the configured chunker for the current RAG settings."""
    if config.TEXT_SPLITTER in ["", "character"]:
        return RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            add_start_index=True,
        )
    elif config.TEXT_SPLITTER == "token":
        log.info(f"Using token text splitter: {config.TIKTOKEN_ENCODING_NAME}")

        tiktoken.get_encoding(str(config.TIKTOKEN_ENCODING_NAME))
        return TokenTextSplitter(
            encoding_name=str(config.TIKTOKEN_ENCODING_NAME),
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            add_start_index=True,
        )
    else:
        raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
    user=None,
) -> bool:
    """Chunk ``docs`` and embed them into ``collection_name``.

    The ``metadata`` dict is stamped onto every chunk alongside the
    embedding-engine snapshot; a ``hash`` in it is checked first so a
    document already stored is rejected as a duplicate. ``overwrite``
    drops the existing collection, ``add`` appends into it.
    """
    log.info(
        f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
    )

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and "hash" in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=collection_name,
            filter={"hash": metadata["hash"]},
        )

        if result is not None:
            existing_doc_ids = result.ids[0]
            if existing_doc_ids:
                log.info(f"Document with hash {metadata['hash']} already exists")
                raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        docs = _text_splitter_for(request.app.state.config).split_documents(docs)

    if len(docs) == 0:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [doc.page_content for doc in docs]
    metadatas = [
        {
            **doc.metadata,
            **(metadata if metadata else {}),
            "embedding_config": json.dumps(
                {
                    "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                    "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                }
            ),
        }
        for doc in docs
    ]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if (
                isinstance(value, datetime)
                or isinstance(value, list)
                or isinstance(value, dict)
            ):
                metadata[key] = str(value)

    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f"collection {collection_name} already exists")

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.info(f"deleting existing collection {collection_name}")
            elif add is False:
                log.info(
                    f"collection {collection_name} already exists, overwrite is False and add is False"
                )
                return True

        log.info(f"adding to collection {collection_name}")
        embedding_function = embedding_function_for(request)

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts)),
            prefix=RAG_EMBEDDING_CONTENT_PREFIX,
            user=user,
        )

        items = [
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "vector": embeddings[idx],
                "metadata": metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        VECTOR_DB_CLIENT.insert(
            collection_name=collection_name,
            items=items,
        )

        return True
    except Exception as e:
        log.exception(e)
        raise e


########################################
# Document processing
########################################


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


class ProcessUrlForm(BaseModel):
    url: str
    collection_name: Optional[str] = None


def _file_document(file) -> Document:
    """Build a single :class:`Document` from a stored file's content."""
    return Document(
        page_content=file.data.get("content", ""),
        metadata={
            **file.meta,
            "name": file.filename,
            "created_by": file.user_id,
            "file_id": file.id,
            "source": file.filename,
        },
    )


def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=None,
):
    """Extract text from ``form_data.file_id`` and index it.

    Three modes, selected by which fields are present: ``content``
    replaces the file's stored text outright (audio pipeline), a
    ``collection_name`` reuses the file's already-processed chunks
    (knowledge add/update), and neither processes the file from disk
    (plain upload flow).
    """
    try:
        file = Files.get_file_by_id(form_data.file_id)

        collection_name = form_data.collection_name

        if collection_name is None:
            collection_name = f"file-{file.id}"

        if form_data.content:
            # Update the content in the file
            # Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)

            try:
                # /files/{file_id}/data/content/update
                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file.id}")
            except:
                # Audio file upload pipeline
                pass

            docs = [
                Document(
                    page_content=form_data.content.replace("<br/>", "\n"),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            text_content = form_data.content
        elif form_data.collection_name:
            # Check if the file has already been processed and save the content
            # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

            result = VECTOR_DB_CLIENT.query(
                collection_name=f"file-{file.id}", filter={"file_id": file.id}
            )

            if result is not None and len(result.ids[0]) > 0:
                docs = [
                    Document(
                        page_content=result.documents[0][idx],
                        metadata=result.metadatas[0][idx],
                    )
                    for idx, id in enumerate(result.ids[0])
                ]
            else:
                docs = [_file_document(file)]

            text_content = file.data.get("content", "")
        else:
            # Process the file and save the content
            # Usage: /files/
            file_path = file.path
            if file_path:
                file_path = Storage.get_file(file_path)
                loader = Loader(
                    engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                    TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                    DOCLING_SERVER_URL=request.app.state.config.DOCLING_SERVER_URL,
                    PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                    DOCUMENT_INTELLIGENCE_ENDPOINT=request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                    DOCUMENT_INTELLIGENCE_KEY=request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                    MISTRAL_OCR_API_KEY=request.app.state.config.MISTRAL_OCR_API_KEY,
                )
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )

                docs = [
                    Document(
                        page_content=doc.page_content,
                        metadata={
                            **doc.metadata,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                    for doc in docs
                ]
            else:
                docs = [_file_document(file)]
            text_content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {text_content}")
        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )

        hash = calculate_sha256_string(text_content)
        Files.update_file_hash_by_id(file.id, hash)

        if not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
            try:
                result = save_docs_to_vector_db(
                    request,
                    docs=docs,
                    collection_name=collection_name,
                    metadata={
                        "file_id": file.id,
                        "name": file.filename,
                        "hash": hash,
                    },
                    add=(True if form_data.collection_name else False),
                    user=user,
                )

                if result:
                    Files.update_file_metadata_by_id(
                        file.id,
                        {
                            "collection_name": collection_name,
                        },
                    )

                    return {
                        "status": True,
                        "collection_name": collection_name,
                        "filename": file.filename,
                        "content": text_content,
                    }
            except Exception as e:
                raise e
        else:
            return {
                "status": True,
                "collection_name": None,
                "filename": file.filename,
                "content": text_content,
            }

    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )


def process_text(
    request: Request,
    form_data: ProcessTextForm,
    user,
):
    """Index plain text under a name or content-derived collection."""
    collection_name = form_data.collection_name
    if collection_name is None:
        # chroma caps collection names at 63 chars; a sha256 digest (64) is
        # one too long, so truncate the derived name.
        collection_name = calculate_sha256_string(form_data.content)[:63]

    docs = [
        Document(
            page_content=form_data.content,
            metadata={"name": form_data.name, "created_by": user.id},
        )
    ]
    text_content = form_data.content
    log.debug(f"text_content: {text_content}")

    result = save_docs_to_vector_db(request, docs, collection_name, user=user)
    if result:
        return {
            "status": True,
            "collection_name": collection_name,
            "content": text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


def process_youtube_video(
    request: Request, form_data: ProcessUrlForm, user
):
    """Fetch a YouTube transcript and index it under the URL's hash."""
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = YoutubeLoader(
            form_data.url,
            language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            proxy_url=request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
        )

        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")

        save_docs_to_vector_db(
            request, docs, collection_name, overwrite=True, user=user
        )

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def process_web(
    request: Request, form_data: ProcessUrlForm, user
):
    """Load a URL's content and index it under the URL's hash."""
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = get_web_loader(
            form_data.url,
            verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {content}")

        if not request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            save_docs_to_vector_db(
                request, docs, collection_name, overwrite=True, user=user
            )
        else:
            collection_name = None

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                    "source": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


########################################
# Web search
########################################


def _require(condition: bool, message: str) -> None:
    """Raise ``message`` when ``condition`` is falsy."""
    if not condition:
        raise Exception(message)


def search_web(request: Request, engine: str, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - KAGI_SEARCH_API_KEY
    - MOJEEK_SEARCH_API_KEY
    - BOCHA_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - EXA_API_KEY
    - PERPLEXITY_API_KEY
    - SOUGOU_API_SID + SOUGOU_API_SK
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    - SERPAPI_API_KEY + SERPAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """
    config = request.app.state.config
    count = config.WEB_SEARCH_RESULT_COUNT
    domains = config.WEB_SEARCH_DOMAIN_FILTER_LIST

    def _web_search(engine: str):
        """Dispatch one configured search engine, validating its credentials."""
        if engine == "searxng":
            _require(
                config.SEARXNG_QUERY_URL,
                "No SEARXNG_QUERY_URL found in environment variables",
            )
            return search_searxng(config.SEARXNG_QUERY_URL, query, count, domains)
        elif engine == "google_pse":
            _require(
                config.GOOGLE_PSE_API_KEY and config.GOOGLE_PSE_ENGINE_ID,
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables",
            )
            return search_google_pse(
                config.GOOGLE_PSE_API_KEY,
                config.GOOGLE_PSE_ENGINE_ID,
                query,
                count,
                domains,
            )
        elif engine == "brave":
            _require(config.BRAVE_SEARCH_API_KEY, "No BRAVE_SEARCH_API_KEY found in environment variables")
            return search_brave(config.BRAVE_SEARCH_API_KEY, query, count, domains)
        elif engine == "kagi":
            _require(config.KAGI_SEARCH_API_KEY, "No KAGI_SEARCH_API_KEY found in environment variables")
            return search_kagi(config.KAGI_SEARCH_API_KEY, query, count, domains)
        elif engine == "mojeek":
            _require(config.MOJEEK_SEARCH_API_KEY, "No MOJEEK_SEARCH_API_KEY found in environment variables")
            return search_mojeek(config.MOJEEK_SEARCH_API_KEY, query, count, domains)
        elif engine == "bocha":
            _require(config.BOCHA_SEARCH_API_KEY, "No BOCHA_SEARCH_API_KEY found in environment variables")
            return search_bocha(config.BOCHA_SEARCH_API_KEY, query, count, domains)
        elif engine == "serpstack":
            _require(config.SERPSTACK_API_KEY, "No SERPSTACK_API_KEY found in environment variables")
            return search_serpstack(
                config.SERPSTACK_API_KEY,
                query,
                count,
                domains,
                https_enabled=config.SERPSTACK_HTTPS,
            )
        elif engine == "serper":
            _require(config.SERPER_API_KEY, "No SERPER_API_KEY found in environment variables")
            return search_serper(config.SERPER_API_KEY, query, count, domains)
        elif engine == "serply":
            _require(config.SERPLY_API_KEY, "No SERPLY_API_KEY found in environment variables")
            return search_serply(config.SERPLY_API_KEY, query, count, domains)
        elif engine == "duckduckgo":
            return search_duckduckgo(query, count, domains)
        elif engine == "tavily":
            _require(config.TAVILY_API_KEY, "No TAVILY_API_KEY found in environment variables")
            return search_tavily(config.TAVILY_API_KEY, query, count, domains)
        elif engine == "searchapi":
            _require(config.SEARCHAPI_API_KEY, "No SEARCHAPI_API_KEY found in environment variables")
            return search_searchapi(
                config.SEARCHAPI_API_KEY, config.SEARCHAPI_ENGINE, query, count, domains
            )
        elif engine == "serpapi":
            _require(config.SERPAPI_API_KEY, "No SERPAPI_API_KEY found in environment variables")
            return search_serpapi(
                config.SERPAPI_API_KEY, config.SERPAPI_ENGINE, query, count, domains
            )
        elif engine == "jina":
            return search_jina(config.JINA_API_KEY, query, count)
        elif engine == "bing":
            return search_bing(
                config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
                config.BING_SEARCH_V7_ENDPOINT,
                str(DEFAULT_LOCALE),
                query,
                count,
                domains,
            )
        elif engine == "exa":
            return search_exa(config.EXA_API_KEY, query, count, domains)
        elif engine == "perplexity":
            return search_perplexity(config.PERPLEXITY_API_KEY, query, count, domains)
        elif engine == "sougou":
            _require(
                config.SOUGOU_API_SID and config.SOUGOU_API_SK,
                "No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables",
            )
            return search_sougou(config.SOUGOU_API_SID, config.SOUGOU_API_SK, query, count, domains)
        else:
            raise Exception("No search engine API key found in environment variables")

    # TODO: add playwright to search the web
    return _web_search(engine)


########################################
# Batch file processing
########################################


class BatchProcessFilesForm(BaseModel):
    files: List[FileModel]
    collection_name: str


class BatchProcessFilesResult(BaseModel):
    file_id: str
    status: str
    error: Optional[str] = None


class BatchProcessFilesResponse(BaseModel):
    results: List[BatchProcessFilesResult]
    errors: List[BatchProcessFilesResult]


def process_files_batch(
    request: Request,
    form_data: BatchProcessFilesForm,
    user,
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.
    """
    results: List[BatchProcessFilesResult] = []
    errors: List[BatchProcessFilesResult] = []
    collection_name = form_data.collection_name

    # Prepare all documents first
    all_docs: List[Document] = []
    for file in form_data.files:
        try:
            text_content = file.data.get("content", "")

            docs: List[Document] = [
                Document(
                    page_content=text_content.replace("<br/>", "\n"),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            hash = calculate_sha256_string(text_content)
            Files.update_file_hash_by_id(file.id, hash)
            Files.update_file_data_by_id(file.id, {"content": text_content})

            all_docs.extend(docs)
            results.append(BatchProcessFilesResult(file_id=file.id, status="prepared"))

        except Exception as e:
            log.error(f"process_files_batch: Error processing file {file.id}: {str(e)}")
            errors.append(
                BatchProcessFilesResult(file_id=file.id, status="failed", error=str(e))
            )

    # Save all documents in one batch
    if all_docs:
        try:
            save_docs_to_vector_db(
                request=request,
                docs=all_docs,
                collection_name=collection_name,
                add=True,
                user=user,
            )

            # Update all files with collection name
            for result in results:
                Files.update_file_metadata_by_id(
                    result.file_id, {"collection_name": collection_name}
                )
                result.status = "completed"

        except Exception as e:
            log.error(
                f"process_files_batch: Error saving documents to vector DB: {str(e)}"
            )
            for result in results:
                result.status = "failed"
                errors.append(
                    BatchProcessFilesResult(file_id=result.file_id, error=str(e))
                )

    return BatchProcessFilesResponse(results=results, errors=errors)
