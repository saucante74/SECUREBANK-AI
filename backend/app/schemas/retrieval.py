from pydantic import BaseModel, ConfigDict

from app.schemas.documents import Chunk


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float
