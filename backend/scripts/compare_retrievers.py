import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import fsum
from time import perf_counter
from typing import Protocol

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from app.core.config import settings
from app.schemas.documents import Chunk
from app.schemas.evaluation import EvaluationCase, EvaluationReport
from app.schemas.retrieval import RetrievalResult
from app.services.bm25 import BM25Retriever
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.reranking import FlashRankReranker
from app.services.retrieval_evaluation import (
    SYNTHETIC_EVALUATION_CASES,
    evaluate_cases,
)
from scripts.demo_rag_retrieval import prepare_pipeline

TOP_K = 3
ENGINE_NAMES = ("BM25", "Qdrant", "RRF", "RRF + FlashRank")

type Timer = Callable[[], float]


class SearchEngine(Protocol):
    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]: ...


class SemanticRetriever:
    def __init__(
        self,
        embedding_service: LocalEmbeddingService,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]:
        query_vector = self._embedding_service.embed_text(question)
        return self._vector_store.search(query_vector, top_k=top_k)


@dataclass(frozen=True)
class ComparisonPipeline:
    chunks: list[Chunk]
    engines: Mapping[str, SearchEngine]
    qdrant_point_count: int


@dataclass(frozen=True)
class EngineComparison:
    results_by_case_id: dict[str, list[RetrievalResult]]
    latency_by_case_id: dict[str, float]
    report_at_1: EvaluationReport
    report_at_3: EvaluationReport

    @property
    def mean_latency_seconds(self) -> float:
        return fsum(self.latency_by_case_id.values()) / len(self.latency_by_case_id)


def validate_results(
    chunks: Sequence[Chunk],
    results: Sequence[RetrievalResult],
) -> None:
    chunks_by_id = {(chunk.document_id, chunk.id): chunk for chunk in chunks}
    for result in results:
        key = (result.chunk.document_id, result.chunk.id)
        if chunks_by_id.get(key) != result.chunk:
            raise ValueError("Retriever returned inconsistent chunk metadata")


def prepare_comparison(
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    flashrank_reranker: FlashRankReranker,
    point_counter: Callable[[Sequence[Chunk]], int],
) -> ComparisonPipeline:
    rag_pipeline = prepare_pipeline(
        chunker,
        embedding_service,
        vector_store,
        flashrank_reranker,
        point_counter,
    )
    engines: dict[str, SearchEngine] = {
        "BM25": BM25Retriever(rag_pipeline.chunks),
        "Qdrant": SemanticRetriever(embedding_service, vector_store),
        "RRF": rag_pipeline.hybrid_retriever,
        "RRF + FlashRank": rag_pipeline.rag_retriever,
    }
    return ComparisonPipeline(
        chunks=rag_pipeline.chunks,
        engines=engines,
        qdrant_point_count=rag_pipeline.point_count,
    )


def evaluate_engine(
    engine: SearchEngine,
    chunks: Sequence[Chunk],
    cases: Sequence[EvaluationCase],
    timer: Timer = perf_counter,
) -> EngineComparison:
    results_by_case_id: dict[str, list[RetrievalResult]] = {}
    latency_by_case_id: dict[str, float] = {}
    for case in cases:
        started_at = timer()
        results = engine.search(case.question, top_k=TOP_K)
        latency_by_case_id[case.id] = timer() - started_at
        validate_results(chunks, results)
        results_by_case_id[case.id] = results
    return EngineComparison(
        results_by_case_id=results_by_case_id,
        latency_by_case_id=latency_by_case_id,
        report_at_1=evaluate_cases(cases, results_by_case_id, k=1),
        report_at_3=evaluate_cases(cases, results_by_case_id, k=3),
    )


def compare_retrievers(
    pipeline: ComparisonPipeline,
    cases: Sequence[EvaluationCase] = SYNTHETIC_EVALUATION_CASES,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    if tuple(pipeline.engines) != ENGINE_NAMES:
        raise ValueError("comparison requires the four configured retrievers")
    return {
        name: evaluate_engine(engine, pipeline.chunks, cases, timer)
        for name, engine in pipeline.engines.items()
    }


def print_metric_table(comparisons: Mapping[str, EngineComparison]) -> None:
    print("\nAggregate metrics")
    print(
        "Engine           | Source Hit@1 | Source Hit@3 | "
        "Evidence Hit@1 | Evidence Hit@3 | Mean latency (ms)"
    )
    for name, comparison in comparisons.items():
        print(
            f"{name:<16} | "
            f"{comparison.report_at_1.mean_source_hit_at_k:>12.3f} | "
            f"{comparison.report_at_3.mean_source_hit_at_k:>12.3f} | "
            f"{comparison.report_at_1.mean_evidence_hit_at_k:>14.3f} | "
            f"{comparison.report_at_3.mean_evidence_hit_at_k:>14.3f} | "
            f"{comparison.mean_latency_seconds * 1_000:>17.3f}"
        )


def print_case_comparisons(
    cases: Sequence[EvaluationCase],
    comparisons: Mapping[str, EngineComparison],
) -> None:
    print("\nPer-question comparison")
    for case in cases:
        print(f"\n{case.id}: {case.question}")
        for name, comparison in comparisons.items():
            results = comparison.results_by_case_id[case.id]
            first_document = results[0].chunk.document_id if results else "No result"
            evaluation = next(
                item for item in comparison.report_at_1.cases if item.case_id == case.id
            )
            print(
                f"  {name:<16} | first={first_document} | "
                f"Source Hit@1={evaluation.source_hit_at_k} | "
                f"Evidence Hit@1={evaluation.evidence_hit_at_k} | "
                f"latency={comparison.latency_by_case_id[case.id] * 1_000:.3f} ms"
            )


def run_comparison(
    pipeline: ComparisonPipeline,
    cases: Sequence[EvaluationCase] = SYNTHETIC_EVALUATION_CASES,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    comparisons = compare_retrievers(pipeline, cases, timer)
    print(f"Evaluation cases: {len(cases)}")
    print(f"Indexed chunks: {len(pipeline.chunks)}")
    print(f"Qdrant points: {pipeline.qdrant_point_count}")
    print_metric_table(comparisons)
    print_case_comparisons(cases, comparisons)
    print("\nLocal latency measurements are not a production benchmark.")
    return comparisons


def create_local_comparison() -> ComparisonPipeline:
    client = QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore.from_settings(settings, client=client)

    def count_points(chunks: Sequence[Chunk]) -> int:
        document_ids = sorted({chunk.document_id for chunk in chunks})
        return client.count(
            collection_name=settings.qdrant_collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=document_ids),
                    )
                ]
            ),
            exact=True,
        ).count

    return prepare_comparison(
        CharacterChunker(chunk_size=180, overlap=30),
        LocalEmbeddingService(),
        vector_store,
        FlashRankReranker(),
        count_points,
    )


def main(
    pipeline_factory: Callable[[], ComparisonPipeline] = create_local_comparison,
) -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        run_comparison(pipeline_factory())
    except FileNotFoundError as error:
        print(f"Local model unavailable: {error}")
        return 1
    except QdrantVectorStoreError as error:
        print(f"Qdrant operation failed: {error}")
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Retriever comparison failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
