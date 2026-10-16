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
from app.services.benchmark_dataset import (
    BENCHMARK_COLLECTION_NAME,
    BenchmarkDataset,
    create_benchmark_chunks,
    load_benchmark_dataset,
)
from app.services.bm25 import BM25Retriever
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_retrieval import RagRetriever
from app.services.reranking import FlashRankReranker
from app.services.retrieval_evaluation import evaluate_cases

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
    cases: tuple[EvaluationCase, ...]
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
    dataset: BenchmarkDataset,
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    flashrank_reranker: FlashRankReranker,
    point_counter: Callable[[Sequence[Chunk]], int],
) -> ComparisonPipeline:
    chunks = create_benchmark_chunks(dataset.documents, chunker)
    embeddings = embedding_service.embed_chunks(chunks)
    vector_store.ensure_collection()
    vector_store.store_chunks(chunks, embeddings)
    point_count = point_counter(chunks)
    if point_count != len(chunks):
        raise ValueError(
            f"Qdrant contains {point_count} points for {len(chunks)} indexed chunks"
        )
    bm25_retriever = BM25Retriever(chunks)
    hybrid_retriever = HybridRetriever(
        bm25_retriever,
        embedding_service,
        vector_store,
    )
    engines: dict[str, SearchEngine] = {
        "BM25": bm25_retriever,
        "Qdrant": SemanticRetriever(embedding_service, vector_store),
        "RRF": hybrid_retriever,
        "RRF + FlashRank": RagRetriever(hybrid_retriever, flashrank_reranker),
    }
    return ComparisonPipeline(
        chunks=chunks,
        cases=dataset.cases,
        engines=engines,
        qdrant_point_count=point_count,
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
    cases: Sequence[EvaluationCase] | None = None,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    if tuple(pipeline.engines) != ENGINE_NAMES:
        raise ValueError("comparison requires the four configured retrievers")
    selected_cases = pipeline.cases if cases is None else cases
    return {
        name: evaluate_engine(engine, pipeline.chunks, selected_cases, timer)
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


def print_failed_cases(
    comparisons: Mapping[str, EngineComparison],
) -> None:
    print("\nFailed questions at rank 3")
    for name, comparison in comparisons.items():
        failed_case_ids = [
            evaluation.case_id
            for evaluation in comparison.report_at_3.cases
            if not evaluation.source_hit_at_k or not evaluation.evidence_hit_at_k
        ]
        displayed = ", ".join(failed_case_ids) if failed_case_ids else "None"
        print(f"  {name}: {displayed}")


def print_flashrank_changes(
    cases: Sequence[EvaluationCase],
    comparisons: Mapping[str, EngineComparison],
) -> None:
    rrf_by_case = {
        evaluation.case_id: evaluation
        for evaluation in comparisons["RRF"].report_at_1.cases
    }
    flashrank_by_case = {
        evaluation.case_id: evaluation
        for evaluation in comparisons["RRF + FlashRank"].report_at_1.cases
    }
    improved: list[str] = []
    degraded: list[str] = []
    for case in cases:
        rrf = rrf_by_case[case.id]
        flashrank = flashrank_by_case[case.id]
        rrf_score = rrf.source_hit_at_k + rrf.evidence_hit_at_k
        flashrank_score = flashrank.source_hit_at_k + flashrank.evidence_hit_at_k
        if flashrank_score > rrf_score:
            improved.append(case.id)
        elif flashrank_score < rrf_score:
            degraded.append(case.id)
    print("\nFlashRank changes versus RRF at rank 1")
    print(f"  Improved: {', '.join(improved) if improved else 'None'}")
    print(f"  Degraded: {', '.join(degraded) if degraded else 'None'}")


def run_comparison(
    pipeline: ComparisonPipeline,
    cases: Sequence[EvaluationCase] | None = None,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    selected_cases = pipeline.cases if cases is None else cases
    comparisons = compare_retrievers(pipeline, selected_cases, timer)
    document_count = len({chunk.document_id for chunk in pipeline.chunks})
    print(f"Documents: {document_count}")
    print(f"Evaluation cases: {len(selected_cases)}")
    print(f"Indexed chunks: {len(pipeline.chunks)}")
    print(f"Qdrant points: {pipeline.qdrant_point_count}")
    print_metric_table(comparisons)
    print_case_comparisons(selected_cases, comparisons)
    print_failed_cases(comparisons)
    print_flashrank_changes(selected_cases, comparisons)
    print("\nLocal latency measurements are not a production benchmark.")
    return comparisons


def create_local_comparison() -> ComparisonPipeline:
    client = QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=BENCHMARK_COLLECTION_NAME,
        client=client,
    )

    def count_points(chunks: Sequence[Chunk]) -> int:
        document_ids = sorted({chunk.document_id for chunk in chunks})
        return client.count(
            collection_name=BENCHMARK_COLLECTION_NAME,
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
        load_benchmark_dataset(),
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
