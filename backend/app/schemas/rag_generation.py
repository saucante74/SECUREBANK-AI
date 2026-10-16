from pydantic import BaseModel, ConfigDict

from app.schemas.documents import Chunk, NonBlankString


class RagGenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: NonBlankString
    answer: NonBlankString
    sources: list[Chunk]
