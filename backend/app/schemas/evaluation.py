from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.documents import NonBlankString

NonEmptyIdentifiers = Annotated[frozenset[NonBlankString], Field(min_length=1)]


class EvaluationCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: NonBlankString
    question: NonBlankString
    expected_document_ids: NonEmptyIdentifiers
    expected_chunk_ids: NonEmptyIdentifiers
    difficulty: Literal["factual", "semantic", "difficult"] | None = None
    rationale: NonBlankString | None = None

    @field_validator(
        "expected_document_ids",
        "expected_chunk_ids",
        mode="before",
    )
    @classmethod
    def validate_unique_identifiers(cls, value: object) -> object:
        if isinstance(value, str):
            raise ValueError("identifiers must be provided as a collection")
        if isinstance(value, (list, tuple)):
            string_values = [item for item in value if isinstance(item, str)]
            if len(string_values) != len(set(string_values)):
                raise ValueError("identifiers must not contain duplicates")
        return value


class CaseEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: NonBlankString
    source_hit_at_k: Literal[0, 1]
    evidence_hit_at_k: Literal[0, 1]


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    k: int = Field(gt=0)
    cases: tuple[CaseEvaluation, ...] = Field(min_length=1)
    mean_source_hit_at_k: float = Field(ge=0.0, le=1.0)
    mean_evidence_hit_at_k: float = Field(ge=0.0, le=1.0)


ConfigurationValue = str | int | float | bool | None


class PublicParameterChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    previous_value: ConfigurationValue
    new_value: ConfigurationValue


class PublicEvaluationMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_hit_at_1: float = Field(ge=0.0, le=1.0)
    source_hit_at_3: float = Field(ge=0.0, le=1.0)
    evidence_hit_at_1: float = Field(ge=0.0, le=1.0)
    evidence_hit_at_3: float = Field(ge=0.0, le=1.0)
    mean_latency_seconds: float = Field(ge=0.0)
    latency_p50_seconds: float | None = Field(default=None, ge=0.0)
    latency_p95_seconds: float | None = Field(default=None, ge=0.0)
    error_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_returned_chunk_count: float | None = Field(default=None, ge=0.0)
    mean_distinct_document_count_at_3: float | None = Field(
        default=None,
        ge=0.0,
        le=3.0,
    )
    mean_source_diversity_at_3: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class PublicEvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    created_at: datetime
    rag_configuration: dict[str, ConfigurationValue]
    parameter_change: PublicParameterChange | None
    measured_metrics: dict[str, PublicEvaluationMetrics] = Field(min_length=1)


class PublicConfigurationChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    previous_value: ConfigurationValue
    new_value: ConfigurationValue


class PublicMetricDelta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    engine: str
    metric: str
    previous_value: float | None
    new_value: float | None
    delta: float | None


class PublicEvaluationComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    previous_run_id: str
    new_run_id: str
    configuration_changes: tuple[PublicConfigurationChange, ...]
    metric_deltas: tuple[PublicMetricDelta, ...]
