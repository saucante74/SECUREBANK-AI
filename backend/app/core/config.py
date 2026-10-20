import math
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "securebank-ai"
    app_version: str = "0.1.0"
    app_env: str = "development"
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "securebank_chunks"
    rag_enabled: bool = False
    rag_corpus_path: Path | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 30.0
    langfuse_enabled: bool = False
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("JWT secret key must contain at least 32 characters")
        return value

    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def validate_jwt_claim_setting(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("JWT claim settings must not be empty")
        return value

    @field_validator("qdrant_url", "qdrant_collection_name")
    @classmethod
    def validate_qdrant_setting(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Qdrant settings must not be empty")
        return value

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def validate_llm_api_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("rag_corpus_path", mode="before")
    @classmethod
    def validate_rag_corpus_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("LLM model must not be empty")
        return value

    @field_validator("llm_base_url", mode="before")
    @classmethod
    def validate_llm_base_url(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("llm_timeout_seconds")
    @classmethod
    def validate_llm_timeout_seconds(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("LLM timeout must be a finite positive number")
        return value

    @field_validator("langfuse_public_key", "langfuse_secret_key", mode="before")
    @classmethod
    def validate_optional_langfuse_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_langfuse_configuration(self) -> "Settings":
        if self.langfuse_enabled and (
            self.langfuse_public_key is None or self.langfuse_secret_key is None
        ):
            raise ValueError(
                "Langfuse public and secret keys are required when observability is enabled"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


settings = Settings()
