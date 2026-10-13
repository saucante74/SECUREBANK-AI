from collections.abc import Sequence

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult

type ChunkKey = tuple[str, str]


def reciprocal_rank_fusion(
    bm25_results: Sequence[RetrievalResult],
    qdrant_results: Sequence[RetrievalResult],
    top_k: int,
    rrf_k: int = 60,
) -> list[RetrievalResult]:
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be a strictly positive integer")
    if not isinstance(rrf_k, int) or isinstance(rrf_k, bool) or rrf_k <= 0:
        raise ValueError("rrf_k must be a strictly positive integer")

    chunks: dict[ChunkKey, Chunk] = {}
    scores: dict[ChunkKey, float] = {}
    first_seen: dict[ChunkKey, int] = {}

    for ranking in (bm25_results, qdrant_results):
        seen_in_ranking: set[ChunkKey] = set()
        for rank, result in enumerate(ranking, start=1):
            key = (result.chunk.document_id, result.chunk.id)
            if key in seen_in_ranking:
                continue
            seen_in_ranking.add(key)
            if key not in chunks:
                chunks[key] = result.chunk
                first_seen[key] = len(first_seen)
                scores[key] = 0.0
            scores[key] += 1 / (rrf_k + rank)

    ranked_keys = sorted(
        scores,
        key=lambda key: (-scores[key], first_seen[key]),
    )
    return [
        RetrievalResult(chunk=chunks[key], score=scores[key])
        for key in ranked_keys[:top_k]
    ]
