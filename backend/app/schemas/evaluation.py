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
