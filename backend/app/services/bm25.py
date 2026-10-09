import re

from rank_bm25 import BM25Okapi

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult

TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        unique_chunks: dict[str, Chunk] = {}
        for chunk in chunks:
            unique_chunks.setdefault(chunk.id, chunk)

        self._chunks = tuple(unique_chunks.values())
        tokenized_chunks = [tokenize(chunk.content) for chunk in self._chunks]
        self._token_sets = tuple(frozenset(tokens) for tokens in tokenized_chunks)
        self._index = BM25Okapi(tokenized_chunks) if any(tokenized_chunks) else None

    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        query_tokens = tokenize(query)
        if not query_tokens or self._index is None:
            return []

        query_token_set = frozenset(query_tokens)
        matching_indices = [
            index
            for index, chunk_tokens in enumerate(self._token_sets)
            if query_token_set & chunk_tokens
        ]
        if not matching_indices:
            return []

        scores = self._index.get_scores(query_tokens)
        ranked_indices = sorted(
            matching_indices,
            key=lambda index: (-float(scores[index]), index),
        )
        return [
            RetrievalResult(
                chunk=self._chunks[index],
                score=float(scores[index]),
            )
            for index in ranked_indices[:top_k]
        ]
