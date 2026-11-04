import json
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.services.benchmark_dataset import (
    BENCHMARK_COLLECTION_NAME,
    BenchmarkDatasetMetadata,
    create_v1_metadata,
)
from app.services.embeddings import DEFAULT_MODEL_NAME

BENCHMARK_RESULTS_DIR = Path(__file__).resolve().parents[2] / "benchmark_results"
BASELINE_RERANKER_MODEL = "ms-marco-MultiBERT-L-12"
BENCHMARK_V2_COLLECTION_NAME = "securebank_benchmark_chunks_v2"
RELEVANCE_METRICS = frozenset(
    {
        "source_hit_at_1",
        "source_hit_at_3",
        "evidence_hit_at_1",
        "evidence_hit_at_3",
    }
)


class EvaluationSummary(Protocol):
    mean_source_hit_at_k: float
    mean_evidence_hit_at_k: float


class EngineComparison(Protocol):
    report_at_1: EvaluationSummary | None
    report_at_3: EvaluationSummary | None
    mean_latency_seconds: float
    latency_p50_seconds: float
    latency_p95_seconds: float
    error_rate: float
    mean_returned_chunk_count: float
    mean_distinct_document_count_at_3: float
    mean_source_diversity_at_3: float
    ir_report_at_1: "IRReportSummary | None"
    ir_report_at_3: "IRReportSummary | None"


class IRAggregateSummary(Protocol):
    value: float | None
    evaluated_question_count: int
    unavailable_question_count: int


class IRReportSummary(Protocol):
    precision_at_k: IRAggregateSummary
    recall_at_k: IRAggregateSummary
    f1_at_k: IRAggregateSummary
    map_at_k: IRAggregateSummary
    success_at_k: IRAggregateSummary
    mrr_at_k: IRAggregateSummary
    ndcg_at_k: IRAggregateSummary


class ParameterChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    previous_value: str | int | float | bool | None
    new_value: str | int | float | bool | None


class IRMetricAggregate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = Field(ge=0.0, le=1.0)
    evaluated_question_count: int = Field(ge=0)
    unavailable_question_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_availability(self) -> "IRMetricAggregate":
        if (self.value is None) != (self.evaluated_question_count == 0):
            raise ValueError("IR metric value must match its evaluated question count")
        return self


class EngineIRMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    judgment_source: Literal["qwen"]
    precision_at_1: IRMetricAggregate
    precision_at_3: IRMetricAggregate
    recall_at_1: IRMetricAggregate
    recall_at_3: IRMetricAggregate
    f1_at_1: IRMetricAggregate
    f1_at_3: IRMetricAggregate
    map_at_3: IRMetricAggregate
    success_at_1: IRMetricAggregate
    success_at_3: IRMetricAggregate
    mrr_at_3: IRMetricAggregate
    ndcg_at_3: IRMetricAggregate


class BaselineRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_id: str = Field(min_length=1, max_length=100)
    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    created_at: datetime
    code_version: str = Field(pattern=r"^[0-9a-f]{40}$")
    rag_configuration: dict[str, str | int | float | bool | None]
    parameter_change: ParameterChange | None
    measured_metrics: dict[str, dict[str, float | None]] = Field(min_length=1)
    ir_metrics: dict[str, EngineIRMetrics] = Field(
        default_factory=dict,
        exclude_if=lambda value: not value,
    )
    expected_behaviors: tuple[str, ...]
    uncomputed_metrics: tuple[str, ...]
    langfuse_trace_ids: tuple[str, ...]

    @field_validator("measured_metrics")
    @classmethod
    def validate_metrics(
        cls,
        value: dict[str, dict[str, float | None]],
    ) -> dict[str, dict[str, float | None]]:
        historical_metrics = {
            "source_hit_at_1",
            "source_hit_at_3",
            "evidence_hit_at_1",
            "evidence_hit_at_3",
            "mean_latency_seconds",
        }
        current_metrics = historical_metrics | {
            "latency_p50_seconds",
            "latency_p95_seconds",
            "error_rate",
            "mean_returned_chunk_count",
            "mean_distinct_document_count_at_3",
            "mean_source_diversity_at_3",
        }
        unit_interval_metrics = {
            "source_hit_at_1",
            "source_hit_at_3",
            "evidence_hit_at_1",
            "evidence_hit_at_3",
            "error_rate",
            "mean_source_diversity_at_3",
        }
        for engine, metrics in value.items():
            if not engine.strip() or frozenset(metrics) not in {
                frozenset(historical_metrics),
                frozenset(current_metrics),
            }:
                raise ValueError("invalid benchmark engine metrics")
            for name, metric in metrics.items():
                if metric is None:
                    if name not in RELEVANCE_METRICS:
                        raise ValueError(
                            "only unavailable relevance metrics may be null"
                        )
                    continue
                maximum = 1.0 if name in unit_interval_metrics else float("inf")
                if metric < 0 or metric > maximum:
                    raise ValueError("benchmark metrics are outside their valid range")
        return value

    @model_validator(mode="after")
    def validate_relevance_availability(self) -> "BaselineRun":
        for metrics in self.measured_metrics.values():
            relevance_values = [metrics[name] for name in RELEVANCE_METRICS]
            missing_count = sum(value is None for value in relevance_values)
            if missing_count not in {0, len(RELEVANCE_METRICS)}:
                raise ValueError("relevance metrics must be entirely available or null")
            if self.benchmark_id.endswith("-v1") and missing_count:
                raise ValueError("v1 relevance metrics must remain numeric")
        return self


class BaselineHistoryError(RuntimeError):
    pass


class BaselineRunNotFoundError(BaselineHistoryError):
    pass


class ConfigurationChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    previous_value: str | int | float | bool | None
    new_value: str | int | float | bool | None


class MetricDelta(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str
    metric: str
    previous_value: float | None
    new_value: float | None
    delta: float | None


class BaselineComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    previous_run_id: str
    new_run_id: str
    configuration_changes: tuple[ConfigurationChange, ...]
    metric_deltas: tuple[MetricDelta, ...]


def current_code_version(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_baseline_run(
    comparisons: Mapping[str, EngineComparison],
    code_version: str,
    created_at: datetime | None = None,
    run_id: str | None = None,
    metadata: BenchmarkDatasetMetadata | None = None,
) -> BaselineRun:
    selected_metadata = metadata or create_v1_metadata()
    measured_metrics = {
        name: {
            "source_hit_at_1": (
                comparison.report_at_1.mean_source_hit_at_k
                if comparison.report_at_1
                else None
            ),
            "source_hit_at_3": (
                comparison.report_at_3.mean_source_hit_at_k
                if comparison.report_at_3
                else None
            ),
            "evidence_hit_at_1": (
                comparison.report_at_1.mean_evidence_hit_at_k
                if comparison.report_at_1
                else None
            ),
            "evidence_hit_at_3": (
                comparison.report_at_3.mean_evidence_hit_at_k
                if comparison.report_at_3
                else None
            ),
            "mean_latency_seconds": comparison.mean_latency_seconds,
            "latency_p50_seconds": comparison.latency_p50_seconds,
            "latency_p95_seconds": comparison.latency_p95_seconds,
            "error_rate": comparison.error_rate,
            "mean_returned_chunk_count": comparison.mean_returned_chunk_count,
            "mean_distinct_document_count_at_3": (
                comparison.mean_distinct_document_count_at_3
            ),
            "mean_source_diversity_at_3": comparison.mean_source_diversity_at_3,
        }
        for name, comparison in comparisons.items()
    }
    ir_metrics = {
        name: build_engine_ir_metrics(comparison)
        for name, comparison in comparisons.items()
        if comparison.ir_report_at_1 is not None
        and comparison.ir_report_at_3 is not None
    }
    collection_name = (
        BENCHMARK_COLLECTION_NAME
        if selected_metadata.corpus_version == "v1"
        else BENCHMARK_V2_COLLECTION_NAME
    )
    return BaselineRun(
        benchmark_id=f"securebank-rag-retrieval-{selected_metadata.corpus_version}",
        run_id=run_id or uuid4().hex,
        created_at=created_at or datetime.now(UTC),
        code_version=code_version,
        rag_configuration={
            "top_k": 3,
            "corpus_version": selected_metadata.corpus_version,
            "chunker": selected_metadata.chunker,
            "chunk_size_characters": selected_metadata.chunk_size,
            "chunk_overlap_characters": selected_metadata.chunk_overlap,
            "embedding_model": DEFAULT_MODEL_NAME,
            "embedding_dimension": 384,
            "qdrant_collection": collection_name,
            "qdrant_distance": "cosine",
            "candidate_multiplier": 3,
            "rrf_k": 60,
            "reranker_model": BASELINE_RERANKER_MODEL,
        },
        parameter_change=None,
        measured_metrics=measured_metrics,
        ir_metrics=ir_metrics,
        expected_behaviors=(
            "answerable cases retrieve their documented source and evidence",
            "unanswerable cases abstain without citations",
            "ambiguous cases avoid unsupported assumptions",
            "grounded answers cite only retrieved passages",
            "sensitive input and output remain masked",
        ),
        uncomputed_metrics=(
            "answer_correctness",
            "abstention_accuracy",
            "citation_correctness",
            "pii_masking_recall",
        ),
        langfuse_trace_ids=(),
    )


def create_ir_metric(metric: IRAggregateSummary) -> IRMetricAggregate:
    return IRMetricAggregate(
        value=metric.value,
        evaluated_question_count=metric.evaluated_question_count,
        unavailable_question_count=metric.unavailable_question_count,
    )


def build_engine_ir_metrics(comparison: EngineComparison) -> EngineIRMetrics:
    report_at_1 = comparison.ir_report_at_1
    report_at_3 = comparison.ir_report_at_3
    if report_at_1 is None or report_at_3 is None:
        raise ValueError("IR metrics require reports at ranks 1 and 3")
    return EngineIRMetrics(
        judgment_source="qwen",
        precision_at_1=create_ir_metric(report_at_1.precision_at_k),
        precision_at_3=create_ir_metric(report_at_3.precision_at_k),
        recall_at_1=create_ir_metric(report_at_1.recall_at_k),
        recall_at_3=create_ir_metric(report_at_3.recall_at_k),
        f1_at_1=create_ir_metric(report_at_1.f1_at_k),
        f1_at_3=create_ir_metric(report_at_3.f1_at_k),
        map_at_3=create_ir_metric(report_at_3.map_at_k),
        success_at_1=create_ir_metric(report_at_1.success_at_k),
        success_at_3=create_ir_metric(report_at_3.success_at_k),
        mrr_at_3=create_ir_metric(report_at_3.mrr_at_k),
        ndcg_at_3=create_ir_metric(report_at_3.ndcg_at_k),
    )


def save_baseline_run(
    run: BaselineRun,
    results_dir: Path = BENCHMARK_RESULTS_DIR,
) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{run.created_at:%Y%m%dT%H%M%SZ}_{run.run_id}.json"
    path.write_text(
        json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_baseline_runs(results_dir: Path = BENCHMARK_RESULTS_DIR) -> list[BaselineRun]:
    if not results_dir.exists():
        return []
    if not results_dir.is_dir():
        raise BaselineHistoryError("benchmark history path is not a directory")
    runs: list[BaselineRun] = []
    try:
        paths = sorted(results_dir.glob("*.json"))
        for path in paths:
            runs.append(BaselineRun.model_validate_json(path.read_text("utf-8")))
    except (OSError, ValidationError) as error:
        raise BaselineHistoryError("benchmark history contains invalid data") from error
    run_ids = [run.run_id for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise BaselineHistoryError(
            "benchmark history contains duplicate run identifiers"
        )
    return sorted(runs, key=lambda run: run.created_at, reverse=True)


def get_baseline_run(
    run_id: str,
    results_dir: Path = BENCHMARK_RESULTS_DIR,
) -> BaselineRun:
    runs = load_baseline_runs(results_dir)
    try:
        return next(run for run in runs if run.run_id == run_id)
    except StopIteration:
        raise BaselineRunNotFoundError("benchmark run was not found") from None


def compare_baseline_runs(
    previous: BaselineRun,
    new: BaselineRun,
) -> BaselineComparison:
    configuration_names = sorted(
        set(previous.rag_configuration) | set(new.rag_configuration)
    )
    configuration_changes = tuple(
        ConfigurationChange(
            name=name,
            previous_value=previous.rag_configuration.get(name),
            new_value=new.rag_configuration.get(name),
        )
        for name in configuration_names
        if previous.rag_configuration.get(name) != new.rag_configuration.get(name)
    )
    engine_names = sorted(set(previous.measured_metrics) | set(new.measured_metrics))
    metric_deltas: list[MetricDelta] = []
    for engine in engine_names:
        previous_metrics = previous.measured_metrics.get(engine, {})
        new_metrics = new.measured_metrics.get(engine, {})
        for metric in sorted(set(previous_metrics) | set(new_metrics)):
            previous_value = previous_metrics.get(metric)
            new_value = new_metrics.get(metric)
            metric_deltas.append(
                MetricDelta(
                    engine=engine,
                    metric=metric,
                    previous_value=previous_value,
                    new_value=new_value,
                    delta=(
                        None
                        if previous_value is None or new_value is None
                        else new_value - previous_value
                    ),
                )
            )
    return BaselineComparison(
        previous_run_id=previous.run_id,
        new_run_id=new.run_id,
        configuration_changes=configuration_changes,
        metric_deltas=tuple(metric_deltas),
    )
