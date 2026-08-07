"""RAG retrieval core: vector queries, hybrid search, and source assembly.

The retrieval domain's routes and services rely on this module for the
embedding-backed collection queries (``query_collection`` and the hybrid
variant), the document helpers used to turn file payloads into searchable
context (``get_sources_from_files``), and the embedding-function factory
(``get_embedding_function``). All vector access goes through the
singleton client in ``jyotigpt.retrieval.vector.connector``.
"""

import hashlib
import logging
import operator
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Sequence, Union

import requests
from huggingface_hub import snapshot_download
from langchain.retrievers.contextual_compression import (
    ContextualCompressionRetriever,
)
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import (
    CallbackManagerForRetrieverRun,
    Callbacks,
)
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.retrievers import BaseRetriever

from jyotigpt.config import (
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
    RAG_EMBEDDING_QUERY_PREFIX,
    VECTOR_DB,
)
from jyotigpt.env import (
    ENABLE_FORWARD_USER_INFO_HEADERS,
    OFFLINE_MODE,
    SRC_LOG_LEVELS,
)
from jyotigpt.models.files import Files
from jyotigpt.models.users import UserModel
from jyotigpt.retrieval.vector.connector import VECTOR_DB_CLIENT
from jyotigpt.retrieval.vector.main import GetResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


##################################
# Retriever building blocks
##################################


class VectorSearchRetriever(BaseRetriever):
    """LangChain-style retriever over a single collection via the DB client."""

    collection_name: Any
    embedding_function: Any
    top_k: int

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        result = VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[
                self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)
            ],
            limit=self.top_k,
        )

        ids = result.ids[0]
        metadatas = result.metadatas[0]
        documents = result.documents[0]

        return [
            Document(metadata=metadatas[idx], page_content=documents[idx])
            for idx in range(len(ids))
        ]


class RerankCompressor(BaseDocumentCompressor):
    """Compresses retrieved documents down to ``top_n`` by relevance score.

    Uses the configured reranking model when one is available; otherwise
    falls back to cosine similarity between the query and each document
    embedding. Optionally drops documents scoring below ``r_score``.
    """

    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = "forbid"
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        if self.reranking_function is not None:
            scores = self.reranking_function.predict(
                [(query, doc.page_content) for doc in documents]
            )
        else:
            from sentence_transformers import util

            query_embedding = self.embedding_function(
                query, RAG_EMBEDDING_QUERY_PREFIX
            )
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents],
                RAG_EMBEDDING_CONTENT_PREFIX,
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        docs_with_scores = list(zip(documents, scores.tolist()))
        if self.r_score:
            docs_with_scores = [
                (doc, score)
                for doc, score in docs_with_scores
                if score >= self.r_score
            ]

        ranked = sorted(
            docs_with_scores, key=operator.itemgetter(1), reverse=True
        )

        final_results = []
        for doc, doc_score in ranked[: self.top_n]:
            metadata = doc.metadata
            metadata["score"] = doc_score
            final_results.append(
                Document(page_content=doc.page_content, metadata=metadata)
            )
        return final_results


##################################
# Vector queries
##################################


def query_doc(
    collection_name: str,
    query_embedding: list[float],
    k: int,
    user: UserModel = None,
):
    """Top-``k`` nearest neighbours of ``query_embedding`` in a collection."""
    try:
        log.debug(f"query_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with limit {k}: {e}")
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    """Every stored item of a collection (ids, documents, metadatas)."""
    try:
        log.debug(f"get_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error getting doc {collection_name}: {e}")
        raise e


def query_doc_with_hybrid_search(
    collection_name: str,
    collection_result: GetResult,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
) -> dict:
    """BM25 + vector ensemble retrieval over one collection, then rerank.

    The ensemble half uses ``collection_result`` for its lexical corpus, so
    callers should fetch the collection once and reuse it across queries.
    """
    try:
        log.debug(f"query_doc_with_hybrid_search:doc {collection_name}")
        bm25_retriever = BM25Retriever.from_texts(
            texts=collection_result.documents[0],
            metadatas=collection_result.metadatas[0],
        )
        bm25_retriever.k = k

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever],
            weights=[0.5, 0.5],
        )
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k_reranker,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)

        distances = [d.metadata.get("score") for d in result]
        documents = [d.page_content for d in result]
        metadatas = [d.metadata for d in result]

        # The reranker may return more than k items; trim back to k
        if k < k_reranker:
            sorted_items = sorted(
                zip(distances, metadatas, documents),
                key=lambda x: x[0],
                reverse=True,
            )[:k]
            distances, documents, metadatas = map(list, zip(*sorted_items))

        result = {
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        }

        log.info(
            "query_doc_with_hybrid_search:result "
            + f'{result["metadatas"]} {result["distances"]}'
        )
        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with hybrid search: {e}")
        raise e


def merge_get_results(get_results: list[dict]) -> dict:
    """Concatenate ``get``-style results (documents/metadatas/ids)."""
    combined_documents = []
    combined_metadatas = []
    combined_ids = []

    for data in get_results:
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])
        combined_ids.extend(data["ids"][0])

    return {
        "documents": [combined_documents],
        "metadatas": [combined_metadatas],
        "ids": [combined_ids],
    }


def merge_and_sort_query_results(query_results: list[dict], k: int) -> dict:
    """Deduplicate by document content, keep best distance, sort desc, top-``k``."""
    combined = dict()  # document hash -> (distance, document, metadata)

    for data in query_results:
        distances = data["distances"][0]
        documents = data["documents"][0]
        metadatas = data["metadatas"][0]

        for distance, document, metadata in zip(distances, documents, metadatas):
            if not isinstance(document, str):
                continue

            doc_hash = hashlib.md5(document.encode()).hexdigest()
            if doc_hash not in combined:
                combined[doc_hash] = (distance, document, metadata)
            elif distance > combined[doc_hash][0]:
                combined[doc_hash] = (distance, document, metadata)

    combined = list(combined.values())
    combined.sort(key=lambda x: x[0], reverse=True)

    sorted_distances, sorted_documents, sorted_metadatas = (
        zip(*combined[:k]) if combined else ([], [], [])
    )

    return {
        "distances": [list(sorted_distances)],
        "documents": [list(sorted_documents)],
        "metadatas": [list(sorted_metadatas)],
    }


def get_all_items_from_collections(collection_names: list[str]) -> dict:
    """Full-context dump of every non-empty collection in ``collection_names``."""
    results = []

    for collection_name in collection_names:
        if not collection_name:
            continue
        try:
            result = get_doc(collection_name=collection_name)
            if result is not None:
                results.append(result.model_dump())
        except Exception as e:
            log.exception(f"Error when querying the collection: {e}")

    return merge_get_results(results)


def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    """Embed every query and retrieve top-``k`` from each collection."""
    results = []
    for query in queries:
        log.debug(f"query_collection:query {query}")
        query_embedding = embedding_function(
            query, prefix=RAG_EMBEDDING_QUERY_PREFIX
        )
        for collection_name in collection_names:
            if not collection_name:
                continue
            try:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,
                    query_embedding=query_embedding,
                )
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error when querying the collection: {e}")

    return merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
) -> dict:
    """Hybrid retrieval across collections, fetches each collection once."""
    results = []
    error = False

    # Fetch collection data once per collection, sequentially; failed
    # fetches are recorded as None and skipped during the query phase.
    collection_results = {}
    for collection_name in collection_names:
        try:
            log.debug(
                "query_collection_with_hybrid_search:"
                f"VECTOR_DB_CLIENT.get:collection {collection_name}"
            )
            collection_results[collection_name] = VECTOR_DB_CLIENT.get(
                collection_name=collection_name
            )
        except Exception as e:
            log.exception(f"Failed to fetch collection {collection_name}: {e}")
            collection_results[collection_name] = None

    log.info(
        f"Starting hybrid search for {len(queries)} queries in "
        f"{len(collection_names)} collections..."
    )

    def process_query(collection_name, query):
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                collection_result=collection_results[collection_name],
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                k_reranker=k_reranker,
                r=r,
            )
            return result, None
        except Exception as e:
            log.exception(
                f"Error when querying the collection with hybrid_search: {e}"
            )
            return None, e

    tasks = [
        (collection_name, query)
        for collection_name in collection_names
        if collection_results[collection_name] is not None
        for query in queries
    ]

    with ThreadPoolExecutor() as executor:
        future_results = [
            executor.submit(process_query, collection_name, query)
            for collection_name, query in tasks
        ]
        task_results = [future.result() for future in future_results]

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        raise Exception(
            "Hybrid search failed for all collections. "
            "Using Non-hybrid search as fallback."
        )

    return merge_and_sort_query_results(results, k=k)


##################################
# Embedding functions
##################################


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
):
    """Return a ``(query, prefix=None, user=None)`` embedder for the engine.

    For local (sentence-transformers) engines the prebuilt embedder is
    wrapped directly; for the ollama/openai engines each call fans out to
    the provider, batching lists into ``embedding_batch_size`` requests.
    """
    if embedding_engine == "":
        return lambda query, prefix=None, user=None: embedding_function.encode(
            query, **({"prompt": prefix} if prefix else {})
        ).tolist()
    elif embedding_engine in ["ollama", "openai"]:

        def embed(query, prefix=None, user=None):
            return generate_embeddings(
                engine=embedding_engine,
                model=embedding_model,
                text=query,
                prefix=prefix,
                url=url,
                key=key,
                user=user,
            )

        def embed_maybe_batched(query, prefix, user):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(
                        embed(query[i : i + embedding_batch_size], prefix, user)
                    )
                return embeddings
            return embed(query, prefix, user)

        return lambda query, prefix=None, user=None: embed_maybe_batched(
            query, prefix, user
        )
    else:
        raise ValueError(f"Unknown embedding engine: {embedding_engine}")


def generate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = "https://api.openai.com/v1",
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    """Embed ``texts`` via an OpenAI-compatible ``/embeddings`` endpoint."""
    try:
        log.debug(
            f"generate_openai_batch_embeddings:model {model} "
            f"batch size: {len(texts)}"
        )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(
            prefix, str
        ):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-JyotiGPT-User-Name": user.name,
                        "X-JyotiGPT-User-Id": user.id,
                        "X-JyotiGPT-User-Email": user.email,
                        "X-JyotiGPT-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        log.error("Embedding response missing 'data' field")
        return None
    except Exception as e:
        log.exception(f"Error generating openai batch embeddings: {e}")
        return None


def generate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    """Embed ``texts`` via an Ollama ``/api/embed`` endpoint."""
    try:
        log.debug(
            f"generate_ollama_batch_embeddings:model {model} "
            f"batch size: {len(texts)}"
        )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(
            prefix, str
        ):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/api/embed",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-JyotiGPT-User-Name": user.name,
                        "X-JyotiGPT-User-Id": user.id,
                        "X-JyotiGPT-User-Email": user.email,
                        "X-JyotiGPT-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "embeddings" in data:
            return data["embeddings"]
        log.error("Embedding response missing 'embeddings' field")
        return None
    except Exception as e:
        log.exception(f"Error generating ollama batch embeddings: {e}")
        return None


def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, list[str]],
    prefix: Union[str, None] = None,
    **kwargs,
):
    """Embed ``text`` (single or batched) for the given provider engine."""
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")

    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f"{prefix}{text_element}" for text_element in text]
        else:
            text = f"{prefix}{text}"

    if engine == "ollama":
        embeddings = generate_ollama_batch_embeddings(
            model=model,
            texts=text if isinstance(text, list) else [text],
            url=url,
            key=key,
            prefix=prefix,
            user=user,
        )
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        embeddings = generate_openai_batch_embeddings(
            model, text if isinstance(text, list) else [text], url, key, prefix, user
        )
        return embeddings[0] if isinstance(text, str) else embeddings


##################################
# Sources
##################################


def get_sources_from_files(
    request,
    files,
    queries,
    embedding_function,
    k,
    reranking_function,
    k_reranker,
    r,
    hybrid_search,
    full_context=False,
):
    """Build the cited-context list for the given file payloads.

    Each file resolves to a context in one of several ways: verbatim docs
    (web-search bypass), the full stored content (full-context mode), the
    raw content when embedding+retrieval is bypassed, or a vector query
    against its collection(s). Duplicate collections across files are
    extracted once.
    """
    log.debug(
        f"files: {files} {queries} {embedding_function} "
        f"{reranking_function} {full_context}"
    )

    extracted_collections = []
    relevant_contexts = []

    for file in files:
        context = None
        if file.get("docs"):
            # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
            context = {
                "documents": [[doc.get("content") for doc in file.get("docs")]],
                "metadatas": [[doc.get("metadata") for doc in file.get("docs")]],
            }
        elif file.get("context") == "full":
            # Manual Full Mode Toggle
            context = {
                "documents": [
                    [file.get("file", {}).get("data", {}).get("content")]
                ],
                "metadatas": [
                    [{"file_id": file.get("id"), "name": file.get("name")}]
                ],
            }
        elif (
            file.get("type") != "web_search"
            and request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
        ):
            # BYPASS_EMBEDDING_AND_RETRIEVAL
            if file.get("type") == "collection":
                file_ids = file.get("data", {}).get("file_ids", [])

                documents = []
                metadatas = []
                for file_id in file_ids:
                    file_object = Files.get_file_by_id(file_id)
                    if file_object:
                        documents.append(file_object.data.get("content", ""))
                        metadatas.append(
                            {
                                "file_id": file_id,
                                "name": file_object.filename,
                                "source": file_object.filename,
                            }
                        )

                context = {"documents": [documents], "metadatas": [metadatas]}

            elif file.get("id"):
                file_object = Files.get_file_by_id(file.get("id"))
                if file_object:
                    context = {
                        "documents": [[file_object.data.get("content", "")]],
                        "metadatas": [
                            [
                                {
                                    "file_id": file.get("id"),
                                    "name": file_object.filename,
                                    "source": file_object.filename,
                                }
                            ]
                        ],
                    }
            elif file.get("file", {}).get("data"):
                context = {
                    "documents": [
                        [file.get("file", {}).get("data", {}).get("content")]
                    ],
                    "metadatas": [
                        [file.get("file", {}).get("data", {}).get("metadata", {})]
                    ],
                }
        else:
            collection_names = []
            if file.get("type") == "collection":
                if file.get("legacy"):
                    collection_names = file.get("collection_names", [])
                else:
                    collection_names.append(file["id"])
            elif file.get("collection_name"):
                collection_names.append(file["collection_name"])
            elif file.get("id"):
                if file.get("legacy"):
                    collection_names.append(f"{file['id']}")
                else:
                    collection_names.append(f"file-{file['id']}")

            collection_names = set(collection_names).difference(
                extracted_collections
            )
            if not collection_names:
                log.debug(f"skipping {file} as it has already been extracted")
                continue

            if full_context:
                try:
                    context = get_all_items_from_collections(collection_names)
                except Exception as e:
                    log.exception(e)
            else:
                try:
                    context = None
                    if file.get("type") == "text":
                        context = file["content"]
                    else:
                        if hybrid_search:
                            try:
                                context = query_collection_with_hybrid_search(
                                    collection_names=collection_names,
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                    reranking_function=reranking_function,
                                    k_reranker=k_reranker,
                                    r=r,
                                )
                            except Exception as e:
                                log.debug(
                                    "Error when using hybrid search, using "
                                    "non hybrid search as fallback."
                                )

                        if (not hybrid_search) or (context is None):
                            context = query_collection(
                                collection_names=collection_names,
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                except Exception as e:
                    log.exception(e)

            extracted_collections.extend(collection_names)

        if context:
            if "data" in file:
                del file["data"]

            relevant_contexts.append({**context, "file": file})

    sources = []
    for context in relevant_contexts:
        try:
            if "documents" in context and "metadatas" in context:
                source = {
                    "source": context["file"],
                    "document": context["documents"][0],
                    "metadata": context["metadatas"][0],
                }
                if "distances" in context and context["distances"]:
                    source["distances"] = context["distances"][0]

                sources.append(source)
        except Exception as e:
            log.exception(e)

    return sources


##################################
# Model paths
##################################


def get_model_path(model: str, update_model: bool = False):
    """Resolve a model name to a local snapshot path via huggingface_hub.

    Returns the input unchanged when it is already a local path or when
    no snapshot can be located; short names are prefixed with the
    ``sentence-transformers`` org.
    """
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")

    local_files_only = not update_model
    if OFFLINE_MODE:
        local_files_only = True

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    log.debug(f"model: {model}")
    log.debug(f"snapshot_kwargs: {snapshot_kwargs}")

    if (
        os.path.exists(model)
        or (("\\" in model or model.count("/") > 1) and local_files_only)
    ):
        # Fully qualified path (or repo-style name offline): use as-is
        return model
    elif "/" not in model:
        model = "sentence-transformers" + "/" + model

    snapshot_kwargs["repo_id"] = model

    try:
        model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f"model_repo_path: {model_repo_path}")
        return model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine model snapshot path: {e}")
        return model
