import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.bm25 import BM25Retriever
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever, RankFusion
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rrf import reciprocal_rank_fusion
from scripts.demo_vector_search import create_chunks, create_documents

QUESTIONS = (
    "Quels revenus, charges et apport sont étudiés pour un crédit immobilier ?",
    "Comment protéger mon logement contre les sinistres ?",
)


@dataclass(frozen=True)
class QueryRankings:
    question: str
    bm25: list[RetrievalResult]
    qdrant: list[RetrievalResult]
    rrf: list[RetrievalResult]


class RecordingRankFusion:
    def __init__(self, fusion: RankFusion = reciprocal_rank_fusion) -> None:
        self._fusion = fusion
        self.bm25_results: list[RetrievalResult] = []
        self.qdrant_results: list[RetrievalResult] = []

    def __call__(
        self,
        bm25_results: Sequence[RetrievalResult],
        qdrant_results: Sequence[RetrievalResult],
        top_k: int,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]:
        self.bm25_results = list(bm25_results)
        self.qdrant_results = list(qdrant_results)
        return self._fusion(
            bm25_results,
            qdrant_results,
            top_k=top_k,
            rrf_k=rrf_k,
        )


def validate_shared_chunks(
    bm25_results: Sequence[RetrievalResult],
    qdrant_results: Sequence[RetrievalResult],
) -> None:
    bm25_chunks = {
        (result.chunk.document_id, result.chunk.id): result.chunk
        for result in bm25_results
    }
    qdrant_chunks = {
        (result.chunk.document_id, result.chunk.id): result.chunk
        for result in qdrant_results
    }
    for key in bm25_chunks.keys() & qdrant_chunks.keys():
        if bm25_chunks[key] != qdrant_chunks[key]:
            raise ValueError(f"Inconsistent chunk metadata for {key[0]} / {key[1]}")


def prepare_pipeline(
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
) -> tuple[list[Chunk], HybridRetriever, RecordingRankFusion]:
    chunks = create_chunks(create_documents(), chunker)
    chunk_embeddings = embedding_service.embed_chunks(chunks)
    vector_store.ensure_collection()
    vector_store.store_chunks(chunks, chunk_embeddings)
    fusion = RecordingRankFusion()
    hybrid_retriever = HybridRetriever(
        BM25Retriever(chunks),
        embedding_service,
        vector_store,
        rank_fusion=fusion,
    )
    return chunks, hybrid_retriever, fusion


def print_ranking(label: str, results: Sequence[RetrievalResult]) -> None:
    print(label)
    if not results:
        print("  No result")
        return
    for rank, result in enumerate(results, start=1):
        print(
            f"  {rank}. score={result.score:.4f} | "
            f"{result.chunk.id} | {result.chunk.title}"
        )


def run_demo(
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    questions: Sequence[str] = QUESTIONS,
) -> list[QueryRankings]:
    chunks, hybrid_retriever, fusion = prepare_pipeline(
        chunker,
        embedding_service,
        vector_store,
    )
    rankings: list[QueryRankings] = []
    print(f"Indexed chunks: {len(chunks)}")
    for question in questions:
        rrf_results = hybrid_retriever.search(question, top_k=3)
        validate_shared_chunks(fusion.bm25_results, fusion.qdrant_results)
        query_rankings = QueryRankings(
            question=question,
            bm25=list(fusion.bm25_results),
            qdrant=list(fusion.qdrant_results),
            rrf=rrf_results,
        )
        rankings.append(query_rankings)
        print(f"\nQuestion: {question}")
        print_ranking("BM25 ranking", query_rankings.bm25)
        print_ranking("Qdrant ranking", query_rankings.qdrant)
        print_ranking("RRF ranking", query_rankings.rrf)
    return rankings


def main(
    embedding_factory: Callable[[], LocalEmbeddingService] = LocalEmbeddingService,
    vector_store_factory: Callable[[], QdrantVectorStore] | None = None,
) -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        embedding_service = embedding_factory()
    except (OSError, RuntimeError) as error:
        print(f"Local embedding model unavailable: {error}")
        return 1

    factory = vector_store_factory or (
        lambda: QdrantVectorStore.from_settings(settings)
    )
    try:
        run_demo(
            CharacterChunker(chunk_size=180, overlap=30),
            embedding_service,
            factory(),
        )
    except QdrantVectorStoreError as error:
        print(f"Qdrant operation failed: {error}")
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Hybrid search demonstration failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
