from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def validate_non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must contain non-whitespace characters")
    return value


NonBlankString = Annotated[str, AfterValidator(validate_non_blank)]


class Document(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: NonBlankString
    content: NonBlankString
    title: NonBlankString
    source: NonBlankString


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: NonBlankString
    document_id: NonBlankString
    content: str = Field(min_length=1)
    position: int = Field(ge=0)
    title: NonBlankString
    source: NonBlankString
