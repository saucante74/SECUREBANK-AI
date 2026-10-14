from collections.abc import Sequence
from typing import Protocol

from app.schemas.retrieval import RetrievalResult
from app.services.rrf import reciprocal_rank_fusion


class LexicalRetriever(Protocol):
    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]: ...


class QueryEmbeddingService(Protocol):
    def embed_text(self, text: str) -> list[float]: ...


class VectorRetriever(Protocol):
    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 3,
    ) -> list[RetrievalResult]: ...


class RankFusion(Protocol):
    def __call__(
        self,
        bm25_results: Sequence[RetrievalResult],
        qdrant_results: Sequence[RetrievalResult],
        top_k: int,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]: ...


class HybridRetriever:
    def __init__(
        self,
        bm25_retriever: LexicalRetriever,
        embedding_service: QueryEmbeddingService,
        vector_retriever: VectorRetriever,
        rank_fusion: RankFusion = reciprocal_rank_fusion,
        candidate_multiplier: int = 3,
        rrf_k: int = 60,
    ) -> None:
        if (
            not isinstance(candidate_multiplier, int)
            or isinstance(candidate_multiplier, bool)
            or candidate_multiplier <= 0
        ):
            raise ValueError("candidate_multiplier must be a strictly positive integer")
        if not isinstance(rrf_k, int) or isinstance(rrf_k, bool) or rrf_k <= 0:
            raise ValueError("rrf_k must be a strictly positive integer")

        self._bm25_retriever = bm25_retriever
        self._embedding_service = embedding_service
        self._vector_retriever = vector_retriever
        self._rank_fusion = rank_fusion
        self._candidate_multiplier = candidate_multiplier
        self._rrf_k = rrf_k

    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must contain non-whitespace characters")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a strictly positive integer")

        candidate_count = top_k * self._candidate_multiplier
        bm25_results = self._bm25_retriever.search(question, top_k=candidate_count)
        query_vector = self._embedding_service.embed_text(question)
        qdrant_results = self._vector_retriever.search(
            query_vector,
            top_k=candidate_count,
        )
        return self._rank_fusion(
            bm25_results,
            qdrant_results,
            top_k=top_k,
            rrf_k=self._rrf_k,
        )
