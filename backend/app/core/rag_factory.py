from collections.abc import Callable
from threading import Lock

from pydantic import ValidationError

from app.core.config import Settings
from app.services.bm25 import BM25Retriever
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.llm import create_openai_llm_service
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_corpus import create_rag_chunks, load_rag_corpus
from app.services.rag_generation import RagGenerationService


class RagConfigurationError(RuntimeError):
    pass


class RagDependencyUnavailableError(RuntimeError):
    pass


def create_rag_generation_service(settings: Settings) -> RagGenerationService:
    if settings.rag_corpus_path is None:
        raise RagConfigurationError("RAG corpus path is not configured")
    if settings.llm_api_key is None:
        raise RagConfigurationError("LLM API key is not configured")

    try:
        corpus = load_rag_corpus(settings.rag_corpus_path)
    except (OSError, ValidationError) as error:
        raise RagConfigurationError("RAG corpus is unavailable or invalid") from error

    chunks = create_rag_chunks(corpus)
    try:
        embedding_service = LocalEmbeddingService()
        chunk_embeddings = embedding_service.embed_chunks(chunks)
    except OSError as error:
        raise RagDependencyUnavailableError(
            "Local embedding model is unavailable"
        ) from error

    vector_store = QdrantVectorStore.from_settings(settings)
    try:
        vector_store.store_chunks(chunks, chunk_embeddings)
    except QdrantVectorStoreError as error:
        raise RagDependencyUnavailableError("Qdrant is unavailable") from error

    retriever = HybridRetriever(
        bm25_retriever=BM25Retriever(chunks),
        embedding_service=embedding_service,
        vector_retriever=vector_store,
    )
    return RagGenerationService(
        retriever=retriever,
        llm_service=create_openai_llm_service(settings),
    )


class RagGenerationServiceProvider:
    def __init__(
        self,
        factory: Callable[[Settings], RagGenerationService] = (
            create_rag_generation_service
        ),
    ) -> None:
        self._factory = factory
        self._service: RagGenerationService | None = None
        self._lock = Lock()

    def get(self, settings: Settings) -> RagGenerationService:
        if self._service is not None:
            return self._service
        with self._lock:
            if self._service is None:
                self._service = self._factory(settings)
            return self._service


rag_generation_service_provider = RagGenerationServiceProvider()
