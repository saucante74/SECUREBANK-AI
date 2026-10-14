from pydantic import BaseModel, ConfigDict, Field, field_validator


class PiiEntity(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)


class PiiMaskRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("text")
    @classmethod
    def validate_non_whitespace_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must contain non-whitespace characters")
        return value


class PiiMaskResponse(BaseModel):
    masked_text: str
