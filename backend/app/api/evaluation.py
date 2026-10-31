import math
from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_settings
from app.core.config import Settings
from app.schemas.evaluation import (
    PublicConfigurationChange,
    PublicEvaluationComparison,
    PublicEvaluationMetrics,
    PublicEvaluationRun,
    PublicMetricDelta,
    PublicParameterChange,
)
from app.services.baseline_history import (
    BaselineHistoryError,
    BaselineRun,
    BaselineRunNotFoundError,
    compare_baseline_runs,
    get_baseline_run,
    load_baseline_runs,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
PUBLIC_NUMERIC_CONFIGURATION_NAMES = frozenset(
    {
        "candidate_multiplier",
        "chunk_overlap_characters",
        "chunk_size_characters",
        "embedding_dimension",
        "rrf_k",
        "top_k",
    }
)
PUBLIC_STRING_CONFIGURATION_VALUES = {
    "embedding_model": frozenset(
        {"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
    ),
    "qdrant_distance": frozenset({"cosine", "dot", "euclid", "manhattan"}),
    "reranker_model": frozenset({"ms-marco-MultiBERT-L-12"}),
    "strategy": frozenset({"bm25", "qdrant", "rrf", "hybrid"}),
}


def history_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Benchmark history is unavailable",
    )


def public_configuration(
    run: BaselineRun,
) -> dict[str, str | int | float | bool | None]:
    return {
        name: value
        for name, value in run.rag_configuration.items()
        if is_public_configuration_value(name, value)
    }


def is_public_configuration_value(
    name: str,
    value: str | int | float | bool | None,
) -> bool:
    if name in PUBLIC_NUMERIC_CONFIGURATION_NAMES:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    allowed_values = PUBLIC_STRING_CONFIGURATION_VALUES.get(name)
    return (
        isinstance(value, str)
        and allowed_values is not None
        and value in allowed_values
    )


def public_run(run: BaselineRun) -> PublicEvaluationRun:
    parameter_change = run.parameter_change
    public_parameter_change = (
        PublicParameterChange.model_validate(parameter_change.model_dump())
        if parameter_change is not None
        and is_public_configuration_value(
            parameter_change.name,
            parameter_change.previous_value,
        )
        and is_public_configuration_value(
            parameter_change.name,
            parameter_change.new_value,
        )
        else None
    )
    return PublicEvaluationRun(
        run_id=run.run_id,
        created_at=run.created_at,
        rag_configuration=public_configuration(run),
        parameter_change=public_parameter_change,
        measured_metrics={
            engine: public_metrics(metrics)
            for engine, metrics in run.measured_metrics.items()
        },
    )


def public_metrics(metrics: Mapping[str, float]) -> PublicEvaluationMetrics:
    return PublicEvaluationMetrics(
        source_hit_at_1=metrics["source_hit_at_1"],
        source_hit_at_3=metrics["source_hit_at_3"],
        evidence_hit_at_1=metrics["evidence_hit_at_1"],
        evidence_hit_at_3=metrics["evidence_hit_at_3"],
        mean_latency_seconds=metrics["mean_latency_seconds"],
        latency_p50_seconds=metrics.get("latency_p50_seconds"),
        latency_p95_seconds=metrics.get("latency_p95_seconds"),
        error_rate=metrics.get("error_rate"),
        mean_returned_chunk_count=metrics.get("mean_returned_chunk_count"),
        mean_distinct_document_count_at_3=metrics.get(
            "mean_distinct_document_count_at_3"
        ),
        mean_source_diversity_at_3=metrics.get("mean_source_diversity_at_3"),
    )


def public_comparison(
    previous: BaselineRun,
    new: BaselineRun,
) -> PublicEvaluationComparison:
    comparison = compare_baseline_runs(
        previous.model_copy(
            update={"rag_configuration": public_configuration(previous)}
        ),
        new.model_copy(update={"rag_configuration": public_configuration(new)}),
    )
    return PublicEvaluationComparison(
        previous_run_id=comparison.previous_run_id,
        new_run_id=comparison.new_run_id,
        configuration_changes=tuple(
            PublicConfigurationChange.model_validate(change.model_dump())
            for change in comparison.configuration_changes
        ),
        metric_deltas=tuple(
            PublicMetricDelta.model_validate(delta.model_dump())
            for delta in comparison.metric_deltas
        ),
    )


@router.get("/runs", response_model=list[PublicEvaluationRun])
def list_runs(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PublicEvaluationRun]:
    try:
        return [
            public_run(run)
            for run in load_baseline_runs(settings.benchmark_results_path)
        ]
    except BaselineHistoryError:
        raise history_error() from None


@router.get("/runs/{run_id}", response_model=PublicEvaluationRun)
def read_run(
    run_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PublicEvaluationRun:
    try:
        return public_run(get_baseline_run(run_id, settings.benchmark_results_path))
    except BaselineRunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        ) from None
    except BaselineHistoryError:
        raise history_error() from None


@router.get("/compare", response_model=PublicEvaluationComparison)
def compare_runs(
    previous_run_id: Annotated[str, Query(min_length=1, max_length=100)],
    new_run_id: Annotated[str, Query(min_length=1, max_length=100)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PublicEvaluationComparison:
    try:
        previous = get_baseline_run(
            previous_run_id,
            settings.benchmark_results_path,
        )
        new = get_baseline_run(new_run_id, settings.benchmark_results_path)
        return public_comparison(previous, new)
    except BaselineRunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        ) from None
    except BaselineHistoryError:
        raise history_error() from None
