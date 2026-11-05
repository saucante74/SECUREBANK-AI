import json
import os
from argparse import ArgumentParser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import fsum
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol
from uuid import uuid5

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny

from app.core.config import settings
from app.schemas.documents import Chunk
from app.schemas.evaluation import (
    EvaluationCase,
    EvaluationReport,
    UnannotatedBenchmarkQuestion,
)
from app.schemas.retrieval import RetrievalResult
from app.services.benchmark_dataset import (
    BENCHMARK_COLLECTION_NAME,
    BenchmarkDataset,
    BenchmarkDatasetMetadata,
    BenchmarkDatasetV2,
    create_benchmark_chunks,
    create_benchmark_v2_chunks,
    create_v1_metadata,
    load_benchmark_dataset,
    load_benchmark_dataset_v2,
)
from app.services.bm25 import BM25Retriever
from app.services.chunking import CharacterChunker
from app.services.embeddings import DEFAULT_MODEL_NAME, LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.qdrant import (
    POINT_NAMESPACE,
    VECTOR_SIZE,
    QdrantVectorStore,
    QdrantVectorStoreError,
)
from app.services.rag_retrieval import RagRetriever
from app.services.relevance_judgments import load_qwen_evaluation_data
from app.services.reranking import FlashRankReranker
from app.services.retrieval_evaluation import (
    IRMetricsReport,
    RelevanceGrade,
    evaluate_cases,
    evaluate_ir_metrics,
)

TOP_K = 3
ENGINE_NAMES = ("BM25", "Qdrant", "RRF", "RRF + FlashRank")
BENCHMARK_V2_COLLECTION_NAME = "securebank_benchmark_chunks_v2"
V2_MANIFEST_PAYLOAD = {
    "benchmark_corpus_version": "v2",
    "benchmark_embedding_model": DEFAULT_MODEL_NAME,
    "benchmark_embedding_dimension": VECTOR_SIZE,
    "benchmark_embedding_distance": "cosine",
}

type Timer = Callable[[], float]
type CorpusVersion = Literal["v1", "v2"]
type BenchmarkQuestion = EvaluationCase | UnannotatedBenchmarkQuestion


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
    cases: tuple[BenchmarkQuestion, ...]
    engines: Mapping[str, SearchEngine]
    qdrant_point_count: int
    metadata: BenchmarkDatasetMetadata = create_v1_metadata()
    relevance_judgments: Mapping[str, Mapping[str, RelevanceGrade]] | None = None


@dataclass(frozen=True)
class EngineComparison:
    results_by_case_id: dict[str, list[RetrievalResult]]
    latency_by_case_id: dict[str, float]
    failed_case_ids: frozenset[str]
    report_at_1: EvaluationReport | None
    report_at_3: EvaluationReport | None
    ir_report_at_1: IRMetricsReport | None = None
    ir_report_at_3: IRMetricsReport | None = None
    metadata: BenchmarkDatasetMetadata = create_v1_metadata()

    @property
    def mean_latency_seconds(self) -> float:
        return fsum(self.latency_by_case_id.values()) / len(self.latency_by_case_id)

    @property
    def latency_p50_seconds(self) -> float:
        return percentile(tuple(self.latency_by_case_id.values()), 0.5)

    @property
    def latency_p95_seconds(self) -> float:
        return percentile(tuple(self.latency_by_case_id.values()), 0.95)

    @property
    def error_rate(self) -> float:
        return len(self.failed_case_ids) / len(self.results_by_case_id)

    @property
    def mean_returned_chunk_count(self) -> float:
        return fsum(len(results) for results in self.results_by_case_id.values()) / len(
            self.results_by_case_id
        )

    @property
    def mean_distinct_document_count_at_3(self) -> float:
        counts = (
            len({result.chunk.document_id for result in results[:TOP_K]})
            for results in self.results_by_case_id.values()
        )
        return fsum(counts) / len(self.results_by_case_id)

    @property
    def mean_source_diversity_at_3(self) -> float:
        diversities = (
            source_diversity_at_3(results)
            for results in self.results_by_case_id.values()
        )
        return fsum(diversities) / len(self.results_by_case_id)


def percentile(values: Sequence[float], quantile: float) -> float:
    ordered_values = sorted(values)
    if not ordered_values:
        raise ValueError("percentile values must not be empty")
    position = (len(ordered_values) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    fraction = position - lower_index
    return (
        ordered_values[lower_index] * (1 - fraction)
        + ordered_values[upper_index] * fraction
    )


def source_diversity_at_3(results: Sequence[RetrievalResult]) -> float:
    selected_results = results[:TOP_K]
    if not selected_results:
        return 0.0
    distinct_documents = {result.chunk.document_id for result in selected_results}
    return len(distinct_documents) / len(selected_results)


def validate_results(
    chunks: Sequence[Chunk],
    results: Sequence[RetrievalResult],
) -> None:
    chunks_by_id = {(chunk.document_id, chunk.id): chunk for chunk in chunks}
    for result in results:
        key = (result.chunk.document_id, result.chunk.id)
        if chunks_by_id.get(key) != result.chunk:
            raise ValueError("Retriever returned inconsistent chunk metadata")


def corpus_fingerprint(
    chunks: Sequence[Chunk],
    metadata: BenchmarkDatasetMetadata,
) -> str:
    serialized = json.dumps(
        {
            "metadata": metadata.model_dump(mode="json"),
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def v2_manifest(
    chunks: Sequence[Chunk],
    metadata: BenchmarkDatasetMetadata,
) -> dict[str, str | int]:
    return {
        **V2_MANIFEST_PAYLOAD,
        "benchmark_corpus_fingerprint": corpus_fingerprint(chunks, metadata),
    }


def validate_v2_collection(
    client: QdrantClient,
    chunks: Sequence[Chunk],
    metadata: BenchmarkDatasetMetadata,
) -> int:
    expected_manifest = v2_manifest(chunks, metadata)
    expected_chunks = {(chunk.document_id, chunk.id) for chunk in chunks}
    try:
        collection = client.get_collection(BENCHMARK_V2_COLLECTION_NAME)
        vectors = collection.config.params.vectors
        if (
            not hasattr(vectors, "size")
            or vectors.size != VECTOR_SIZE
            or vectors.distance != Distance.COSINE
        ):
            raise ValueError(
                "Qdrant benchmark v2 collection has incompatible vector configuration"
            )
        point_count = client.count(
            collection_name=BENCHMARK_V2_COLLECTION_NAME,
            exact=True,
        ).count
        if point_count != len(chunks):
            raise ValueError(
                "Qdrant benchmark v2 collection has an incompatible point count: "
                f"expected {len(chunks)}, found {point_count}"
            )
        found_chunks: set[tuple[str, str]] = set()
        offset: object | None = None
        while True:
            points, next_offset = client.scroll(
                collection_name=BENCHMARK_V2_COLLECTION_NAME,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload
                if not isinstance(payload, dict):
                    raise ValueError(
                        "Qdrant benchmark v2 collection contains invalid payloads"
                    )
                if any(
                    payload.get(key) != value
                    for key, value in expected_manifest.items()
                ):
                    raise ValueError(
                        "Qdrant benchmark v2 collection has incompatible corpus or "
                        "embedding metadata"
                    )
                document_id = payload.get("document_id")
                chunk_id = payload.get("chunk_id")
                if not isinstance(document_id, str) or not isinstance(chunk_id, str):
                    raise ValueError(
                        "Qdrant benchmark v2 collection contains invalid chunk identifiers"
                    )
                found_chunks.add((document_id, chunk_id))
            if next_offset is None:
                break
            offset = next_offset
        if found_chunks != expected_chunks:
            raise ValueError(
                "Qdrant benchmark v2 collection has incompatible chunk identifiers"
            )
        return point_count
    except ApiException as error:
        raise QdrantVectorStoreError(
            "Unable to validate Qdrant benchmark v2 collection"
        ) from error


def prepare_v2_collection(
    client: QdrantClient,
    vector_store: QdrantVectorStore,
    chunks: Sequence[Chunk],
    metadata: BenchmarkDatasetMetadata,
    embedding_service: LocalEmbeddingService,
    index_chunks: bool,
) -> int:
    try:
        collection_exists = client.collection_exists(BENCHMARK_V2_COLLECTION_NAME)
    except ApiException as error:
        raise QdrantVectorStoreError(
            "Unable to inspect Qdrant benchmark v2 collection"
        ) from error
    if collection_exists:
        return validate_v2_collection(client, chunks, metadata)
    if not index_chunks:
        raise ValueError(
            "Qdrant benchmark v2 collection does not exist; index it before reuse"
        )
    embeddings = embedding_service.embed_chunks(chunks)
    vector_store.store_chunks(chunks, embeddings)
    point_ids = [
        str(uuid5(POINT_NAMESPACE, f"{chunk.document_id}\x00{chunk.id}"))
        for chunk in chunks
    ]
    try:
        client.set_payload(
            collection_name=BENCHMARK_V2_COLLECTION_NAME,
            payload=v2_manifest(chunks, metadata),
            points=point_ids,
            wait=True,
        )
    except ApiException as error:
        raise QdrantVectorStoreError(
            "Unable to record Qdrant benchmark v2 collection metadata"
        ) from error
    return validate_v2_collection(client, chunks, metadata)


def benchmark_collection_name(corpus_version: CorpusVersion) -> str:
    return (
        BENCHMARK_V2_COLLECTION_NAME
        if corpus_version == "v2"
        else BENCHMARK_COLLECTION_NAME
    )


def prepare_comparison(
    dataset: BenchmarkDataset | BenchmarkDatasetV2,
    chunker: CharacterChunker | None,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    flashrank_reranker: FlashRankReranker,
    point_counter: Callable[[Sequence[Chunk]], int],
    index_chunks: bool = True,
    relevance_judgments: Mapping[str, Mapping[str, RelevanceGrade]] | None = None,
) -> ComparisonPipeline:
    if isinstance(dataset, BenchmarkDatasetV2):
        chunks = create_benchmark_v2_chunks(dataset.documents)
        cases: tuple[BenchmarkQuestion, ...] = dataset.reference_questions
    else:
        chunks = create_benchmark_chunks(dataset.documents, chunker)
        cases = dataset.cases
    if index_chunks:
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
        cases=cases,
        engines=engines,
        qdrant_point_count=point_count,
        metadata=dataset.metadata,
        relevance_judgments=relevance_judgments,
    )


def evaluate_engine(
    engine: SearchEngine,
    chunks: Sequence[Chunk],
    cases: Sequence[BenchmarkQuestion],
    timer: Timer = perf_counter,
    metadata: BenchmarkDatasetMetadata | None = None,
    relevance_judgments: Mapping[str, Mapping[str, RelevanceGrade]] | None = None,
) -> EngineComparison:
    selected_metadata = metadata or create_v1_metadata()
    results_by_case_id: dict[str, list[RetrievalResult]] = {}
    latency_by_case_id: dict[str, float] = {}
    failed_case_ids: set[str] = set()
    for case in cases:
        started_at = timer()
        try:
            results = engine.search(case.question, top_k=TOP_K)
            validate_results(chunks, results)
        except Exception:
            results = []
            failed_case_ids.add(case.id)
        latency_by_case_id[case.id] = timer() - started_at
        results_by_case_id[case.id] = results
    report_at_1 = None
    report_at_3 = None
    ir_report_at_1 = None
    ir_report_at_3 = None
    if selected_metadata.relevance_annotations:
        annotated_cases = tuple(
            case for case in cases if isinstance(case, EvaluationCase)
        )
        if len(annotated_cases) != len(cases):
            raise ValueError("annotated corpus requires annotated evaluation cases")
        report_at_1 = evaluate_cases(annotated_cases, results_by_case_id, k=1)
        report_at_3 = evaluate_cases(annotated_cases, results_by_case_id, k=3)
        if relevance_judgments is not None:
            ir_report_at_1 = evaluate_ir_metrics(
                results_by_case_id,
                relevance_judgments,
                k=1,
            )
            ir_report_at_3 = evaluate_ir_metrics(
                results_by_case_id,
                relevance_judgments,
                k=3,
            )
    return EngineComparison(
        results_by_case_id=results_by_case_id,
        latency_by_case_id=latency_by_case_id,
        failed_case_ids=frozenset(failed_case_ids),
        report_at_1=report_at_1,
        report_at_3=report_at_3,
        ir_report_at_1=ir_report_at_1,
        ir_report_at_3=ir_report_at_3,
        metadata=selected_metadata,
    )


def compare_retrievers(
    pipeline: ComparisonPipeline,
    cases: Sequence[BenchmarkQuestion] | None = None,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    if tuple(pipeline.engines) != ENGINE_NAMES:
        raise ValueError("comparison requires the four configured retrievers")
    selected_cases = pipeline.cases if cases is None else cases
    selected_judgments = (
        {case.id: pipeline.relevance_judgments[case.id] for case in selected_cases}
        if pipeline.relevance_judgments is not None
        else None
    )
    return {
        name: evaluate_engine(
            engine,
            pipeline.chunks,
            selected_cases,
            timer,
            pipeline.metadata,
            selected_judgments,
        )
        for name, engine in pipeline.engines.items()
    }


def print_metric_table(comparisons: Mapping[str, EngineComparison]) -> None:
    print("\nAggregate metrics")
    print(
        "Engine           | Source Hit@1 | Source Hit@3 | "
        "Evidence Hit@1 | Evidence Hit@3 | P50 (ms) | P95 (ms) | Error rate | "
        "Mean chunks | Mean docs@3 | Diversity@3"
    )
    for name, comparison in comparisons.items():
        source_hit_at_1 = metric_or_na(
            comparison.report_at_1.mean_source_hit_at_k
            if comparison.report_at_1
            else None
        )
        source_hit_at_3 = metric_or_na(
            comparison.report_at_3.mean_source_hit_at_k
            if comparison.report_at_3
            else None
        )
        evidence_hit_at_1 = metric_or_na(
            comparison.report_at_1.mean_evidence_hit_at_k
            if comparison.report_at_1
            else None
        )
        evidence_hit_at_3 = metric_or_na(
            comparison.report_at_3.mean_evidence_hit_at_k
            if comparison.report_at_3
            else None
        )
        print(
            f"{name:<16} | "
            f"{source_hit_at_1:>12} | "
            f"{source_hit_at_3:>12} | "
            f"{evidence_hit_at_1:>14} | "
            f"{evidence_hit_at_3:>14} | "
            f"{comparison.latency_p50_seconds * 1_000:>8.3f} | "
            f"{comparison.latency_p95_seconds * 1_000:>8.3f} | "
            f"{comparison.error_rate:>10.3f} | "
            f"{comparison.mean_returned_chunk_count:>11.3f} | "
            f"{comparison.mean_distinct_document_count_at_3:>11.3f} | "
            f"{comparison.mean_source_diversity_at_3:>11.3f}"
        )


def metric_or_na(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def print_case_comparisons(
    cases: Sequence[BenchmarkQuestion],
    comparisons: Mapping[str, EngineComparison],
) -> None:
    print("\nPer-question comparison")
    for case in cases:
        print(f"\n{case.id}: {case.question}")
        for name, comparison in comparisons.items():
            results = comparison.results_by_case_id[case.id]
            first_document = results[0].chunk.document_id if results else "No result"
            evaluation = (
                next(
                    item
                    for item in comparison.report_at_1.cases
                    if item.case_id == case.id
                )
                if comparison.report_at_1
                else None
            )
            print(
                f"  {name:<16} | first={first_document} | "
                f"Source Hit@1={evaluation.source_hit_at_k if evaluation else 'N/A'} | "
                f"Evidence Hit@1={evaluation.evidence_hit_at_k if evaluation else 'N/A'} | "
                f"latency={comparison.latency_by_case_id[case.id] * 1_000:.3f} ms"
            )


def print_failed_cases(
    comparisons: Mapping[str, EngineComparison],
) -> None:
    print("\nFailed questions at rank 3")
    for name, comparison in comparisons.items():
        if comparison.report_at_3 is None:
            print(f"  {name}: N/A")
            continue
        failed_case_ids = [
            evaluation.case_id
            for evaluation in comparison.report_at_3.cases
            if not evaluation.source_hit_at_k or not evaluation.evidence_hit_at_k
        ]
        displayed = ", ".join(failed_case_ids) if failed_case_ids else "None"
        print(f"  {name}: {displayed}")


def print_flashrank_changes(
    cases: Sequence[BenchmarkQuestion],
    comparisons: Mapping[str, EngineComparison],
) -> None:
    if comparisons["RRF"].report_at_1 is None:
        print("\nFlashRank changes versus RRF at rank 1")
        print("  N/A")
        return
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
    cases: Sequence[BenchmarkQuestion] | None = None,
    timer: Timer = perf_counter,
) -> dict[str, EngineComparison]:
    selected_cases = pipeline.cases if cases is None else cases
    comparisons = compare_retrievers(pipeline, selected_cases, timer)
    document_count = len({chunk.document_id for chunk in pipeline.chunks})
    print(f"Corpus version: {pipeline.metadata.corpus_version}")
    print(f"Chunker: {pipeline.metadata.chunker}")
    print(f"Chunk size: {pipeline.metadata.chunk_size}")
    print(f"Chunk overlap: {pipeline.metadata.chunk_overlap}")
    print(f"Documents: {document_count}")
    print(f"Evaluation cases: {len(selected_cases)}")
    print(f"Indexed chunks: {len(pipeline.chunks)}")
    print(f"Qdrant points: {pipeline.qdrant_point_count}")
    print_metric_table(comparisons)
    print_case_comparisons(selected_cases, comparisons)
    print_failed_cases(comparisons)
    print_flashrank_changes(selected_cases, comparisons)
    print("\nDiversity@3 is 0 when a question returns no chunks.")
    print("\nLocal latency measurements are not a production benchmark.")
    return comparisons


def create_local_comparison(
    index_chunks: bool = True,
    corpus_version: CorpusVersion = "v1",
    judgments_path: Path | None = None,
) -> ComparisonPipeline:
    client = QdrantClient(url=settings.qdrant_url)
    collection_name = benchmark_collection_name(corpus_version)
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=collection_name,
        client=client,
    )

    def count_points(chunks: Sequence[Chunk]) -> int:
        document_ids = sorted({chunk.document_id for chunk in chunks})
        return client.count(
            collection_name=collection_name,
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

    dataset: BenchmarkDataset | BenchmarkDatasetV2
    chunker: CharacterChunker | None
    if corpus_version == "v2":
        dataset = load_benchmark_dataset_v2()
        corpus_metadata = dataset.metadata
        chunker = None
        chunks = create_benchmark_v2_chunks(dataset.documents)
        relevance_judgments = None
        if judgments_path is not None:
            evaluation_data = load_qwen_evaluation_data(
                dataset,
                {chunk.id for chunk in chunks},
                corpus_fingerprint(chunks, corpus_metadata),
                judgments_path=judgments_path,
            )
            cases = evaluation_data.cases
            relevance_judgments = evaluation_data.judgments_by_question_id
            dataset = dataset.model_copy(
                update={
                    "reference_questions": cases,
                    "metadata": dataset.metadata.model_copy(
                        update={"relevance_annotations": True}
                    ),
                }
            )
        embedding_service = LocalEmbeddingService()
        point_count = prepare_v2_collection(
            client,
            vector_store,
            chunks,
            corpus_metadata,
            embedding_service,
            index_chunks,
        )
        return prepare_comparison(
            dataset,
            chunker,
            embedding_service,
            vector_store,
            FlashRankReranker(),
            lambda selected_chunks: point_count,
            index_chunks=False,
            relevance_judgments=relevance_judgments,
        )
    else:
        dataset = load_benchmark_dataset()
        chunker = CharacterChunker(chunk_size=180, overlap=30)
    return prepare_comparison(
        dataset,
        chunker,
        LocalEmbeddingService(),
        vector_store,
        FlashRankReranker(),
        count_points,
        index_chunks=index_chunks,
    )


def main(
    pipeline_factory: Callable[[], ComparisonPipeline] | None = None,
    corpus_version: CorpusVersion = "v1",
) -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        selected_factory = pipeline_factory or (
            lambda: create_local_comparison(corpus_version=corpus_version)
        )
        run_comparison(selected_factory())
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


def parse_corpus_version() -> CorpusVersion:
    parser = ArgumentParser()
    parser.add_argument(
        "--corpus-version",
        choices=("v1", "v2"),
        default="v1",
    )
    arguments = parser.parse_args()
    return arguments.corpus_version


if __name__ == "__main__":
    raise SystemExit(main(corpus_version=parse_corpus_version()))
