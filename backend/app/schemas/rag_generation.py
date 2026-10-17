from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk, NonBlankString


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
