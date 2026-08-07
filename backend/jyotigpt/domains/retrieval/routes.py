"""Retrieval HTTP routes.

The admin-facing RAG/web-search configuration surface plus the document
processing, web search, and query endpoints. The engine itself lives in
:mod:`jyotigpt.domains.retrieval.service`; these routes declare the HTTP
contract and delegate, keeping the config passthroughs (embedding engine,
chunking, web-search credentials) as thin as they can be.
"""

import logging
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from jyotigpt.config import ENV, RAG_EMBEDDING_QUERY_PREFIX, UPLOAD_DIR
from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.files import Files
from jyotigpt.models.knowledge import Knowledges
from jyotigpt.retrieval.utils import (
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from jyotigpt.retrieval.vector.connector import VECTOR_DB_CLIENT
from jyotigpt.retrieval.web.utils import get_web_loader
from jyotigpt.utils.auth import get_admin_user, get_verified_user
from jyotigpt.utils.misc import calculate_sha256_string

from .service import (
    BatchProcessFilesForm,
    BatchProcessFilesResponse,
    ProcessFileForm,
    ProcessTextForm,
    ProcessUrlForm,
    embedding_function_for,
    get_ef,
    get_rf,
    process_file,
    process_files_batch,
    process_text,
    process_web,
    process_youtube_video,
    save_docs_to_vector_db,
    search_web,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

router = APIRouter()


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class SearchForm(BaseModel):
    query: str


########################################
# Status / configuration
########################################


@router.get("/")
async def get_status(request: Request):
    return {
        "status": True,
        "chunk_size": request.app.state.config.CHUNK_SIZE,
        "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
        "template": request.app.state.config.RAG_TEMPLATE,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    }


@router.get("/embedding")
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        "openai_config": {
            "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
            "key": request.app.state.config.RAG_OPENAI_API_KEY,
        },
        "ollama_config": {
            "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
            "key": request.app.state.config.RAG_OLLAMA_API_KEY,
        },
    }


@router.get("/reranking")
async def get_reraanking_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class OllamaConfigForm(BaseModel):
    url: str
    key: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    ollama_config: Optional[OllamaConfigForm] = None
    embedding_engine: str
    embedding_model: str
    embedding_batch_size: Optional[int] = 1


@router.post("/embedding/update")
async def update_embedding_config(
    request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        request.app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if request.app.state.config.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config is not None:
                request.app.state.config.RAG_OPENAI_API_BASE_URL = (
                    form_data.openai_config.url
                )
                request.app.state.config.RAG_OPENAI_API_KEY = (
                    form_data.openai_config.key
                )

            if form_data.ollama_config is not None:
                request.app.state.config.RAG_OLLAMA_BASE_URL = (
                    form_data.ollama_config.url
                )
                request.app.state.config.RAG_OLLAMA_API_KEY = (
                    form_data.ollama_config.key
                )

            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE = (
                form_data.embedding_batch_size
            )

        request.app.state.ef = get_ef(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
        )

        request.app.state.EMBEDDING_FUNCTION = embedding_function_for(request)

        return {
            "status": True,
            "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
            "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
            "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            "openai_config": {
                "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
                "key": request.app.state.config.RAG_OPENAI_API_KEY,
            },
            "ollama_config": {
                "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
                "key": request.app.state.config.RAG_OLLAMA_API_KEY,
            },
        }
    except Exception as e:
        log.exception(f"Problem updating embedding model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class RerankingModelUpdateForm(BaseModel):
    reranking_model: str


@router.post("/reranking/update")
async def update_reranking_config(
    request: Request, form_data: RerankingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating reranking model: {request.app.state.config.RAG_RERANKING_MODEL} to {form_data.reranking_model}"
    )
    try:
        request.app.state.config.RAG_RERANKING_MODEL = form_data.reranking_model

        try:
            request.app.state.rf = get_rf(
                request.app.state.config.RAG_RERANKING_MODEL,
                True,
            )
        except Exception as e:
            log.error(f"Error loading reranking model: {e}")
            request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = False

        return {
            "status": True,
            "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        }
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def _rag_config(request: Request) -> dict:
    """The full RAG configuration, as returned by GET /config and
    POST /config/update."""
    config = request.app.state.config
    return {
        "status": True,
        # RAG settings
        "RAG_TEMPLATE": config.RAG_TEMPLATE,
        "TOP_K": config.TOP_K,
        "BYPASS_EMBEDDING_AND_RETRIEVAL": config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        "RAG_FULL_CONTEXT": config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        "ENABLE_RAG_HYBRID_SEARCH": config.ENABLE_RAG_HYBRID_SEARCH,
        "TOP_K_RERANKER": config.TOP_K_RERANKER,
        "RELEVANCE_THRESHOLD": config.RELEVANCE_THRESHOLD,
        # Content extraction settings
        "CONTENT_EXTRACTION_ENGINE": config.CONTENT_EXTRACTION_ENGINE,
        "PDF_EXTRACT_IMAGES": config.PDF_EXTRACT_IMAGES,
        "TIKA_SERVER_URL": config.TIKA_SERVER_URL,
        "DOCLING_SERVER_URL": config.DOCLING_SERVER_URL,
        "DOCUMENT_INTELLIGENCE_ENDPOINT": config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        "DOCUMENT_INTELLIGENCE_KEY": config.DOCUMENT_INTELLIGENCE_KEY,
        "MISTRAL_OCR_API_KEY": config.MISTRAL_OCR_API_KEY,
        # Chunking settings
        "TEXT_SPLITTER": config.TEXT_SPLITTER,
        "CHUNK_SIZE": config.CHUNK_SIZE,
        "CHUNK_OVERLAP": config.CHUNK_OVERLAP,
        # File upload settings
        "FILE_MAX_SIZE": config.FILE_MAX_SIZE,
        "FILE_MAX_COUNT": config.FILE_MAX_COUNT,
        # Integration settings
        "ENABLE_GOOGLE_DRIVE_INTEGRATION": config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        "ENABLE_ONEDRIVE_INTEGRATION": config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        "web": {
            "ENABLE_WEB_SEARCH": config.ENABLE_WEB_SEARCH,
            "WEB_SEARCH_ENGINE": config.WEB_SEARCH_ENGINE,
            "WEB_SEARCH_TRUST_ENV": config.WEB_SEARCH_TRUST_ENV,
            "WEB_SEARCH_RESULT_COUNT": config.WEB_SEARCH_RESULT_COUNT,
            "WEB_SEARCH_CONCURRENT_REQUESTS": config.WEB_SEARCH_CONCURRENT_REQUESTS,
            "WEB_SEARCH_DOMAIN_FILTER_LIST": config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            "SEARXNG_QUERY_URL": config.SEARXNG_QUERY_URL,
            "GOOGLE_PSE_API_KEY": config.GOOGLE_PSE_API_KEY,
            "GOOGLE_PSE_ENGINE_ID": config.GOOGLE_PSE_ENGINE_ID,
            "BRAVE_SEARCH_API_KEY": config.BRAVE_SEARCH_API_KEY,
            "KAGI_SEARCH_API_KEY": config.KAGI_SEARCH_API_KEY,
            "MOJEEK_SEARCH_API_KEY": config.MOJEEK_SEARCH_API_KEY,
            "BOCHA_SEARCH_API_KEY": config.BOCHA_SEARCH_API_KEY,
            "SERPSTACK_API_KEY": config.SERPSTACK_API_KEY,
            "SERPSTACK_HTTPS": config.SERPSTACK_HTTPS,
            "SERPER_API_KEY": config.SERPER_API_KEY,
            "SERPLY_API_KEY": config.SERPLY_API_KEY,
            "TAVILY_API_KEY": config.TAVILY_API_KEY,
            "SEARCHAPI_API_KEY": config.SEARCHAPI_API_KEY,
            "SEARCHAPI_ENGINE": config.SEARCHAPI_ENGINE,
            "SERPAPI_API_KEY": config.SERPAPI_API_KEY,
            "SERPAPI_ENGINE": config.SERPAPI_ENGINE,
            "JINA_API_KEY": config.JINA_API_KEY,
            "BING_SEARCH_V7_ENDPOINT": config.BING_SEARCH_V7_ENDPOINT,
            "BING_SEARCH_V7_SUBSCRIPTION_KEY": config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            "EXA_API_KEY": config.EXA_API_KEY,
            "PERPLEXITY_API_KEY": config.PERPLEXITY_API_KEY,
            "SOUGOU_API_SID": config.SOUGOU_API_SID,
            "SOUGOU_API_SK": config.SOUGOU_API_SK,
            "WEB_LOADER_ENGINE": config.WEB_LOADER_ENGINE,
            "ENABLE_WEB_LOADER_SSL_VERIFICATION": config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            "PLAYWRIGHT_WS_URL": config.PLAYWRIGHT_WS_URL,
            "PLAYWRIGHT_TIMEOUT": config.PLAYWRIGHT_TIMEOUT,
            "FIRECRAWL_API_KEY": config.FIRECRAWL_API_KEY,
            "FIRECRAWL_API_BASE_URL": config.FIRECRAWL_API_BASE_URL,
            "TAVILY_EXTRACT_DEPTH": config.TAVILY_EXTRACT_DEPTH,
            "YOUTUBE_LOADER_LANGUAGE": config.YOUTUBE_LOADER_LANGUAGE,
            "YOUTUBE_LOADER_PROXY_URL": config.YOUTUBE_LOADER_PROXY_URL,
            "YOUTUBE_LOADER_TRANSLATION": request.app.state.YOUTUBE_LOADER_TRANSLATION,
        },
    }


@router.get("/config")
async def get_rag_config(request: Request, user=Depends(get_admin_user)):
    return _rag_config(request)


class WebConfig(BaseModel):
    ENABLE_WEB_SEARCH: Optional[bool] = None
    WEB_SEARCH_ENGINE: Optional[str] = None
    WEB_SEARCH_TRUST_ENV: Optional[bool] = None
    WEB_SEARCH_RESULT_COUNT: Optional[int] = None
    WEB_SEARCH_CONCURRENT_REQUESTS: Optional[int] = None
    WEB_SEARCH_DOMAIN_FILTER_LIST: Optional[List[str]] = []
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    SEARXNG_QUERY_URL: Optional[str] = None
    GOOGLE_PSE_API_KEY: Optional[str] = None
    GOOGLE_PSE_ENGINE_ID: Optional[str] = None
    BRAVE_SEARCH_API_KEY: Optional[str] = None
    KAGI_SEARCH_API_KEY: Optional[str] = None
    MOJEEK_SEARCH_API_KEY: Optional[str] = None
    BOCHA_SEARCH_API_KEY: Optional[str] = None
    SERPSTACK_API_KEY: Optional[str] = None
    SERPSTACK_HTTPS: Optional[bool] = None
    SERPER_API_KEY: Optional[str] = None
    SERPLY_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    SEARCHAPI_API_KEY: Optional[str] = None
    SEARCHAPI_ENGINE: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    SERPAPI_ENGINE: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    BING_SEARCH_V7_ENDPOINT: Optional[str] = None
    BING_SEARCH_V7_SUBSCRIPTION_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    SOUGOU_API_SID: Optional[str] = None
    SOUGOU_API_SK: Optional[str] = None
    WEB_LOADER_ENGINE: Optional[str] = None
    ENABLE_WEB_LOADER_SSL_VERIFICATION: Optional[bool] = None
    PLAYWRIGHT_WS_URL: Optional[str] = None
    PLAYWRIGHT_TIMEOUT: Optional[int] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_API_BASE_URL: Optional[str] = None
    TAVILY_EXTRACT_DEPTH: Optional[str] = None
    YOUTUBE_LOADER_LANGUAGE: Optional[List[str]] = None
    YOUTUBE_LOADER_PROXY_URL: Optional[str] = None
    YOUTUBE_LOADER_TRANSLATION: Optional[str] = None


class ConfigForm(BaseModel):
    # RAG settings
    RAG_TEMPLATE: Optional[str] = None
    TOP_K: Optional[int] = None
    BYPASS_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    RAG_FULL_CONTEXT: Optional[bool] = None

    # Hybrid search settings
    ENABLE_RAG_HYBRID_SEARCH: Optional[bool] = None
    TOP_K_RERANKER: Optional[int] = None
    RELEVANCE_THRESHOLD: Optional[float] = None

    # Content extraction settings
    CONTENT_EXTRACTION_ENGINE: Optional[str] = None
    PDF_EXTRACT_IMAGES: Optional[bool] = None
    TIKA_SERVER_URL: Optional[str] = None
    DOCLING_SERVER_URL: Optional[str] = None
    DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
    MISTRAL_OCR_API_KEY: Optional[str] = None

    # Chunking settings
    TEXT_SPLITTER: Optional[str] = None
    CHUNK_SIZE: Optional[int] = None
    CHUNK_OVERLAP: Optional[int] = None

    # File upload settings
    FILE_MAX_SIZE: Optional[int] = None
    FILE_MAX_COUNT: Optional[int] = None

    # Integration settings
    ENABLE_GOOGLE_DRIVE_INTEGRATION: Optional[bool] = None
    ENABLE_ONEDRIVE_INTEGRATION: Optional[bool] = None

    # Web search settings
    web: Optional[WebConfig] = None


@router.post("/config/update")
async def update_rag_config(
    request: Request, form_data: ConfigForm, user=Depends(get_admin_user)
):
    config = request.app.state.config

    def _apply(name, value):
        """Assign ``value`` onto the config unless it was not provided."""
        if value is not None:
            setattr(config, name, value)

    # RAG settings
    _apply("RAG_TEMPLATE", form_data.RAG_TEMPLATE)
    _apply("TOP_K", form_data.TOP_K)
    _apply("BYPASS_EMBEDDING_AND_RETRIEVAL", form_data.BYPASS_EMBEDDING_AND_RETRIEVAL)
    _apply("RAG_FULL_CONTEXT", form_data.RAG_FULL_CONTEXT)

    # Hybrid search settings
    _apply("ENABLE_RAG_HYBRID_SEARCH", form_data.ENABLE_RAG_HYBRID_SEARCH)
    # Free up memory if hybrid search is disabled
    if not config.ENABLE_RAG_HYBRID_SEARCH:
        request.app.state.rf = None

    _apply("TOP_K_RERANKER", form_data.TOP_K_RERANKER)
    _apply("RELEVANCE_THRESHOLD", form_data.RELEVANCE_THRESHOLD)

    # Content extraction settings
    _apply("CONTENT_EXTRACTION_ENGINE", form_data.CONTENT_EXTRACTION_ENGINE)
    _apply("PDF_EXTRACT_IMAGES", form_data.PDF_EXTRACT_IMAGES)
    _apply("TIKA_SERVER_URL", form_data.TIKA_SERVER_URL)
    _apply("DOCLING_SERVER_URL", form_data.DOCLING_SERVER_URL)
    _apply("DOCUMENT_INTELLIGENCE_ENDPOINT", form_data.DOCUMENT_INTELLIGENCE_ENDPOINT)
    _apply("DOCUMENT_INTELLIGENCE_KEY", form_data.DOCUMENT_INTELLIGENCE_KEY)
    _apply("MISTRAL_OCR_API_KEY", form_data.MISTRAL_OCR_API_KEY)

    # Chunking settings
    _apply("TEXT_SPLITTER", form_data.TEXT_SPLITTER)
    _apply("CHUNK_SIZE", form_data.CHUNK_SIZE)
    _apply("CHUNK_OVERLAP", form_data.CHUNK_OVERLAP)

    # File upload settings
    _apply("FILE_MAX_SIZE", form_data.FILE_MAX_SIZE)
    _apply("FILE_MAX_COUNT", form_data.FILE_MAX_COUNT)

    # Integration settings
    _apply("ENABLE_GOOGLE_DRIVE_INTEGRATION", form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION)
    _apply("ENABLE_ONEDRIVE_INTEGRATION", form_data.ENABLE_ONEDRIVE_INTEGRATION)

    if form_data.web is not None:
        # Web search settings
        _apply("ENABLE_WEB_SEARCH", form_data.web.ENABLE_WEB_SEARCH)
        _apply("WEB_SEARCH_ENGINE", form_data.web.WEB_SEARCH_ENGINE)
        _apply("WEB_SEARCH_TRUST_ENV", form_data.web.WEB_SEARCH_TRUST_ENV)
        _apply("WEB_SEARCH_RESULT_COUNT", form_data.web.WEB_SEARCH_RESULT_COUNT)
        _apply("WEB_SEARCH_CONCURRENT_REQUESTS", form_data.web.WEB_SEARCH_CONCURRENT_REQUESTS)
        _apply("WEB_SEARCH_DOMAIN_FILTER_LIST", form_data.web.WEB_SEARCH_DOMAIN_FILTER_LIST)
        _apply("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL)
        _apply("SEARXNG_QUERY_URL", form_data.web.SEARXNG_QUERY_URL)
        _apply("GOOGLE_PSE_API_KEY", form_data.web.GOOGLE_PSE_API_KEY)
        _apply("GOOGLE_PSE_ENGINE_ID", form_data.web.GOOGLE_PSE_ENGINE_ID)
        _apply("BRAVE_SEARCH_API_KEY", form_data.web.BRAVE_SEARCH_API_KEY)
        _apply("KAGI_SEARCH_API_KEY", form_data.web.KAGI_SEARCH_API_KEY)
        _apply("MOJEEK_SEARCH_API_KEY", form_data.web.MOJEEK_SEARCH_API_KEY)
        _apply("BOCHA_SEARCH_API_KEY", form_data.web.BOCHA_SEARCH_API_KEY)
        _apply("SERPSTACK_API_KEY", form_data.web.SERPSTACK_API_KEY)
        _apply("SERPSTACK_HTTPS", form_data.web.SERPSTACK_HTTPS)
        _apply("SERPER_API_KEY", form_data.web.SERPER_API_KEY)
        _apply("SERPLY_API_KEY", form_data.web.SERPLY_API_KEY)
        _apply("TAVILY_API_KEY", form_data.web.TAVILY_API_KEY)
        _apply("SEARCHAPI_API_KEY", form_data.web.SEARCHAPI_API_KEY)
        _apply("SEARCHAPI_ENGINE", form_data.web.SEARCHAPI_ENGINE)
        _apply("SERPAPI_API_KEY", form_data.web.SERPAPI_API_KEY)
        _apply("SERPAPI_ENGINE", form_data.web.SERPAPI_ENGINE)
        _apply("JINA_API_KEY", form_data.web.JINA_API_KEY)
        _apply("BING_SEARCH_V7_ENDPOINT", form_data.web.BING_SEARCH_V7_ENDPOINT)
        _apply("BING_SEARCH_V7_SUBSCRIPTION_KEY", form_data.web.BING_SEARCH_V7_SUBSCRIPTION_KEY)
        _apply("EXA_API_KEY", form_data.web.EXA_API_KEY)
        _apply("PERPLEXITY_API_KEY", form_data.web.PERPLEXITY_API_KEY)
        _apply("SOUGOU_API_SID", form_data.web.SOUGOU_API_SID)
        _apply("SOUGOU_API_SK", form_data.web.SOUGOU_API_SK)

        # Web loader settings
        _apply("WEB_LOADER_ENGINE", form_data.web.WEB_LOADER_ENGINE)
        _apply("ENABLE_WEB_LOADER_SSL_VERIFICATION", form_data.web.ENABLE_WEB_LOADER_SSL_VERIFICATION)
        _apply("PLAYWRIGHT_WS_URL", form_data.web.PLAYWRIGHT_WS_URL)
        _apply("PLAYWRIGHT_TIMEOUT", form_data.web.PLAYWRIGHT_TIMEOUT)
        _apply("FIRECRAWL_API_KEY", form_data.web.FIRECRAWL_API_KEY)
        _apply("FIRECRAWL_API_BASE_URL", form_data.web.FIRECRAWL_API_BASE_URL)
        _apply("TAVILY_EXTRACT_DEPTH", form_data.web.TAVILY_EXTRACT_DEPTH)
        _apply("YOUTUBE_LOADER_LANGUAGE", form_data.web.YOUTUBE_LOADER_LANGUAGE)
        _apply("YOUTUBE_LOADER_PROXY_URL", form_data.web.YOUTUBE_LOADER_PROXY_URL)
        request.app.state.YOUTUBE_LOADER_TRANSLATION = (
            form_data.web.YOUTUBE_LOADER_TRANSLATION
        )

    return _rag_config(request)


########################################
# Document processing
########################################


@router.post("/process/file")
def process_file_route(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
):
    return process_file(request, form_data, user=user)


@router.post("/process/text")
def process_text_route(
    request: Request,
    form_data: ProcessTextForm,
    user=Depends(get_verified_user),
):
    return process_text(request, form_data, user=user)


@router.post("/process/youtube")
def process_youtube_route(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    return process_youtube_video(request, form_data, user=user)


@router.post("/process/web")
def process_web_route(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    return process_web(request, form_data, user=user)


@router.post("/process/web/search")
async def process_web_search(
    request: Request, form_data: SearchForm, user=Depends(get_verified_user)
):
    try:
        logging.info(
            f"trying to web search with {request.app.state.config.WEB_SEARCH_ENGINE, form_data.query}"
        )
        web_results = await run_in_threadpool(
            search_web,
            request,
            request.app.state.config.WEB_SEARCH_ENGINE,
            form_data.query,
        )
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    log.debug(f"web_results: {web_results}")

    try:
        urls = [result.link for result in web_results]
        loader = get_web_loader(
            urls,
            verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            trust_env=request.app.state.config.WEB_SEARCH_TRUST_ENV,
        )
        docs = await loader.aload()
        urls = [
            doc.metadata["source"] for doc in docs
        ]  # only keep URLs which could be retrieved

        if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            return {
                "status": True,
                "collection_name": None,
                "filenames": urls,
                "docs": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc in docs
                ],
                "loaded_count": len(docs),
            }
        else:
            collection_names = []
            for doc_idx, doc in enumerate(docs):
                if doc and doc.page_content:
                    collection_name = f"web-search-{calculate_sha256_string(form_data.query + '-' + urls[doc_idx])}"[
                        :63
                    ]

                    collection_names.append(collection_name)
                    await run_in_threadpool(
                        save_docs_to_vector_db,
                        request,
                        [doc],
                        collection_name,
                        overwrite=True,
                        user=user,
                    )

            return {
                "status": True,
                "collection_names": collection_names,
                "filenames": urls,
                "loaded_count": len(docs),
            }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/process/files/batch")
def process_files_batch_route(
    request: Request,
    form_data: BatchProcessFilesForm,
    user=Depends(get_verified_user),
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.
    """
    return process_files_batch(request, form_data, user=user)


########################################
# Query
########################################


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/doc")
def query_doc_handler(
    request: Request,
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            collection_results = {}
            collection_results[form_data.collection_name] = VECTOR_DB_CLIENT.get(
                collection_name=form_data.collection_name
            )
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                collection_result=collection_results[form_data.collection_name],
                query=form_data.query,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=request.app.state.rf,
                k_reranker=form_data.k_reranker
                or request.app.state.config.TOP_K_RERANKER,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
                user=user,
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query_embedding=request.app.state.EMBEDDING_FUNCTION(
                    form_data.query, prefix=RAG_EMBEDDING_QUERY_PREFIX, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                user=user,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/collection")
def query_collection_handler(
    request: Request,
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=request.app.state.rf,
                k_reranker=form_data.k_reranker
                or request.app.state.config.TOP_K_RERANKER,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


########################################
# Vector DB operations
########################################


class DeleteForm(BaseModel):
    collection_name: str
    file_id: str


@router.post("/delete")
def delete_entries_from_collection(form_data: DeleteForm, user=Depends(get_admin_user)):
    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=form_data.collection_name):
            file = Files.get_file_by_id(form_data.file_id)
            hash = file.hash

            VECTOR_DB_CLIENT.delete(
                collection_name=form_data.collection_name,
                metadata={"hash": hash},
            )
            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        log.exception(e)
        return {"status": False}


@router.post("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    VECTOR_DB_CLIENT.reset()
    Knowledges.delete_all_knowledge()


@router.post("/reset/uploads")
def reset_upload_dir(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    try:
        # Check if the directory exists
        if os.path.exists(folder):
            # Iterate over all the files and directories in the specified directory
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"The directory {folder} does not exist")
    except Exception as e:
        log.exception(f"Failed to process the directory {folder}. Reason: {e}")
    return True


if ENV == "dev":

    @router.get("/ef/{text}")
    async def get_embeddings(request: Request, text: Optional[str] = "Hello World!"):
        return {
            "result": request.app.state.EMBEDDING_FUNCTION(
                text, prefix=RAG_EMBEDDING_QUERY_PREFIX
            )
        }
