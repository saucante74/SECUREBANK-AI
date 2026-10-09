from pydantic import BaseModel, ConfigDict, Field


class PiiEntity(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)
