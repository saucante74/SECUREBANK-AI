from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.documents import Chunk, NonBlankString


class RagAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=3, ge=1, le=5, strict=True)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must contain non-whitespace characters")
        return value


class RagCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference: int = Field(ge=1)
    document_id: NonBlankString
    chunk_id: NonBlankString


class RagGenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: NonBlankString
    answer: NonBlankString
    sources: list[Chunk]
    citations: list[RagCitation]
    abstained: bool
