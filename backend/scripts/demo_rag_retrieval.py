import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from app.core.config import settings
from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.bm25 import BM25Retriever
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_retrieval import (
    HybridSearchEngine,
    RagRetriever,
    RerankingEngine,
)
from app.services.reranking import FlashRankReranker
from scripts.demo_hybrid_search import RecordingRankFusion, validate_shared_chunks
from scripts.demo_vector_search import create_chunks, create_documents

TOP_K = 3
CANDIDATE_MULTIPLIER = 3
QUESTIONS = (
    "Quels revenus, charges et apport sont pris en compte pour un crédit immobilier ?",
    "Comment protéger mon logement contre les sinistres ?",
    "Puis-je rembourser mon prêt immobilier avant la date prévue ?",
)

type Timer = Callable[[], float]
type PointCounter = Callable[[Sequence[Chunk]], int]


@dataclass(frozen=True)
class QueryRun:
    question: str
    rrf: list[RetrievalResult]
    final: list[RetrievalResult]
    candidate_request: int
    hybrid_seconds: float
    reranking_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class PreparedPipeline:
    chunks: list[Chunk]
    rag_retriever: RagRetriever
    hybrid_retriever: "MeasuredHybridRetriever"
    reranker: "MeasuredReranker"
    fusion: RecordingRankFusion
    point_count: int


class MeasuredHybridRetriever:
    def __init__(
        self,
        retriever: HybridSearchEngine,
        timer: Timer = perf_counter,
    ) -> None:
        self._retriever = retriever
        self._timer = timer
        self.results: list[RetrievalResult] = []
        self.requested_top_k = 0
        self.duration_seconds = 0.0

    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]:
        started_at = self._timer()
        self.requested_top_k = top_k
        self.results = self._retriever.search(question, top_k=top_k)
        self.duration_seconds = self._timer() - started_at
        return self.results


class MeasuredReranker:
    def __init__(
        self,
        reranker: RerankingEngine,
        timer: Timer = perf_counter,
    ) -> None:
        self._reranker = reranker
        self._timer = timer
        self.candidates: list[RetrievalResult] = []
        self.results: list[RetrievalResult] = []
        self.duration_seconds = 0.0

    def rerank(
        self,
        question: str,
        results: Sequence[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        started_at = self._timer()
        self.candidates = list(results)
        self.results = self._reranker.rerank(question, results, top_k)
        self.duration_seconds = self._timer() - started_at
        return self.results


def validate_results(
    chunks: Sequence[Chunk],
    rrf_results: Sequence[RetrievalResult],
    final_results: Sequence[RetrievalResult],
) -> None:
    chunks_by_id = {(chunk.document_id, chunk.id): chunk for chunk in chunks}
    rrf_by_id = {
        (result.chunk.document_id, result.chunk.id): result.chunk
        for result in rrf_results
    }
    if len(rrf_by_id) != len(rrf_results):
        raise ValueError("RRF returned duplicate chunk identifiers")
    for key, chunk in rrf_by_id.items():
        if chunks_by_id.get(key) != chunk:
            raise ValueError("RRF returned inconsistent chunk metadata")
    for result in final_results:
        key = (result.chunk.document_id, result.chunk.id)
        if rrf_by_id.get(key) != result.chunk:
            raise ValueError("FlashRank returned inconsistent chunk metadata")


def prepare_pipeline(
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    flashrank_reranker: RerankingEngine,
    point_counter: PointCounter,
    timer: Timer = perf_counter,
) -> PreparedPipeline:
    chunks = create_chunks(create_documents(), chunker)
    embeddings = embedding_service.embed_chunks(chunks)
    vector_store.ensure_collection()
    vector_store.store_chunks(chunks, embeddings)
    point_count = point_counter(chunks)
    if point_count != len(chunks):
        raise ValueError(
            f"Qdrant contains {point_count} points for {len(chunks)} indexed chunks"
        )
    fusion = RecordingRankFusion()
    hybrid = HybridRetriever(
        BM25Retriever(chunks),
        embedding_service,
        vector_store,
        rank_fusion=fusion,
    )
    measured_hybrid = MeasuredHybridRetriever(hybrid, timer)
    measured_reranker = MeasuredReranker(flashrank_reranker, timer)
    rag_retriever = RagRetriever(measured_hybrid, measured_reranker)
    return PreparedPipeline(
        chunks=chunks,
        rag_retriever=rag_retriever,
        hybrid_retriever=measured_hybrid,
        reranker=measured_reranker,
        fusion=fusion,
        point_count=point_count,
    )


def print_ranking(label: str, results: Sequence[RetrievalResult]) -> None:
    print(label)
    if not results:
        print("  No result")
        return
    for rank, result in enumerate(results, start=1):
        print(
            f"  {rank}. score={result.score:.6f} | "
            f"{result.chunk.id} | {result.chunk.title}"
        )


def run_demo(
    pipeline: PreparedPipeline,
    questions: Sequence[str] = QUESTIONS,
    timer: Timer = perf_counter,
) -> list[QueryRun]:
    runs: list[QueryRun] = []
    print(f"Indexed chunks: {len(pipeline.chunks)}")
    print(f"Qdrant points: {pipeline.point_count}")
    for question in questions:
        started_at = timer()
        final_results = pipeline.rag_retriever.search(question, top_k=TOP_K)
        total_seconds = timer() - started_at
        rrf_results = list(pipeline.hybrid_retriever.results)
        validate_shared_chunks(
            pipeline.fusion.bm25_results,
            pipeline.fusion.qdrant_results,
        )
        validate_results(pipeline.chunks, rrf_results, final_results)
        if pipeline.hybrid_retriever.requested_top_k != TOP_K * CANDIDATE_MULTIPLIER:
            raise ValueError("RagRetriever requested an unexpected candidate count")
        run = QueryRun(
            question=question,
            rrf=rrf_results,
            final=final_results,
            candidate_request=pipeline.hybrid_retriever.requested_top_k,
            hybrid_seconds=pipeline.hybrid_retriever.duration_seconds,
            reranking_seconds=pipeline.reranker.duration_seconds,
            total_seconds=total_seconds,
        )
        runs.append(run)
        print(f"\nQuestion: {run.question}")
        print(f"Candidate request: {run.candidate_request}")
        print(f"Candidates passed to FlashRank: {len(pipeline.reranker.candidates)}")
        print_ranking("RRF ranking", run.rrf)
        print_ranking("FlashRank ranking", run.final)
        print(f"Hybrid search time: {run.hybrid_seconds:.6f} s")
        print(f"Reranking time: {run.reranking_seconds:.6f} s")
        print(f"Total time: {run.total_seconds:.6f} s")
    return runs


def create_local_pipeline() -> PreparedPipeline:
    client = QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore.from_settings(settings, client=client)
    return prepare_pipeline(
        CharacterChunker(chunk_size=180, overlap=30),
        LocalEmbeddingService(),
        vector_store,
        FlashRankReranker(),
        lambda chunks: (
            client.count(
                collection_name=settings.qdrant_collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchAny(
                                any=sorted({chunk.document_id for chunk in chunks})
                            ),
                        )
                    ]
                ),
                exact=True,
            ).count
        ),
    )


def main(
    pipeline_factory: Callable[[], PreparedPipeline] = create_local_pipeline,
) -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        run_demo(pipeline_factory())
    except FileNotFoundError as error:
        print(f"Local model unavailable: {error}")
        return 1
    except QdrantVectorStoreError as error:
        print(f"Qdrant operation failed: {error}")
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"RAG retrieval demonstration failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
