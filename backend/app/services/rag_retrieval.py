from collections.abc import Sequence
from typing import Protocol

from app.schemas.retrieval import RetrievalResult


class HybridSearchEngine(Protocol):
    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]: ...


class RerankingEngine(Protocol):
    def rerank(
        self,
        question: str,
        results: Sequence[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]: ...


class RagRetriever:
    def __init__(
        self,
        hybrid_retriever: HybridSearchEngine,
        reranker: RerankingEngine,
        candidate_multiplier: int = 3,
    ) -> None:
        if (
            not isinstance(candidate_multiplier, int)
            or isinstance(candidate_multiplier, bool)
            or candidate_multiplier <= 0
        ):
            raise ValueError("candidate_multiplier must be a strictly positive integer")
        self._hybrid_retriever = hybrid_retriever
        self._reranker = reranker
        self._candidate_multiplier = candidate_multiplier

    def search(self, question: str, top_k: int) -> list[RetrievalResult]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must contain non-whitespace characters")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a strictly positive integer")

        candidate_count = top_k * self._candidate_multiplier
        candidates = self._hybrid_retriever.search(question, top_k=candidate_count)
        if not candidates:
            return []
        return self._reranker.rerank(question, candidates, top_k=top_k)[:top_k]
