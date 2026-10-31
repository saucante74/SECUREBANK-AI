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
    user_database_path: Path = BACKEND_DIR / "data" / "users.sqlite3"
    session_lifetime_seconds: int = 900
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_trusted_origins: str = (
        "http://localhost:5173,http://localhost:8080,"
        "http://127.0.0.1:5173,http://127.0.0.1:8080"
    )
    login_attempt_limit: int = 5
    login_attempt_window_seconds: int = 300
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "securebank_chunks"
    benchmark_results_path: Path = BACKEND_DIR / "benchmark_results"
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

    @field_validator("user_database_path", "benchmark_results_path")
    @classmethod
    def validate_user_database_path(cls, value: Path) -> Path:
        if not str(value).strip():
            raise ValueError("User database path must not be empty")
        return value

    @field_validator(
        "session_lifetime_seconds",
        "login_attempt_limit",
        "login_attempt_window_seconds",
    )
    @classmethod
    def validate_positive_auth_setting(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(
                "Authentication duration and limit settings must be positive"
            )
        return value

    @field_validator("auth_trusted_origins")
    @classmethod
    def validate_auth_trusted_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("At least one authentication origin is required")
        if any(not origin.startswith(("http://", "https://")) for origin in origins):
            raise ValueError("Authentication origins must use HTTP or HTTPS")
        return ",".join(origins)

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

    @model_validator(mode="after")
    def validate_session_cookie_configuration(self) -> "Settings":
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires a secure session cookie")
        if self.app_env == "production" and not self.session_cookie_secure:
            raise ValueError("Production requires a secure session cookie")
        return self

    @property
    def trusted_auth_origins(self) -> frozenset[str]:
        return frozenset(self.auth_trusted_origins.split(","))

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


settings = Settings()
