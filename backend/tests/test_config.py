from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_ALGORITHM", raising=False)
    monkeypatch.delenv("JWT_ISSUER", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("USER_DATABASE_PATH", raising=False)
    monkeypatch.delenv("SESSION_LIFETIME_SECONDS", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SAMESITE", raising=False)
    monkeypatch.delenv("AUTH_TRUSTED_ORIGINS", raising=False)
    monkeypatch.delenv("LOGIN_ATTEMPT_LIMIT", raising=False)
    monkeypatch.delenv("LOGIN_ATTEMPT_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_COLLECTION_NAME", raising=False)
    monkeypatch.delenv("RAG_ENABLED", raising=False)
    monkeypatch.delenv("RAG_CORPUS_PATH", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "securebank-ai"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.jwt_secret_key is None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer is None
    assert settings.jwt_audience is None
    assert (
        settings.user_database_path
        == Path(__file__).resolve().parents[1] / "data" / "users.sqlite3"
    )
    assert settings.session_lifetime_seconds == 900
    assert settings.session_cookie_secure is False
    assert settings.session_cookie_samesite == "lax"
    assert settings.trusted_auth_origins == frozenset(
        {
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        }
    )
    assert settings.login_attempt_limit == 5
    assert settings.login_attempt_window_seconds == 300
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_name == "securebank_chunks"
    assert settings.rag_enabled is False
    assert settings.rag_corpus_path is None
    assert settings.llm_api_key is None
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.llm_base_url is None
    assert settings.llm_timeout_seconds == 30.0
    assert settings.langfuse_enabled is False
    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None
    assert str(settings.langfuse_host) == "http://localhost:3000/"


def test_settings_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "securebank-ai-test")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ISSUER", "securebank-ai-test")
    monkeypatch.setenv("JWT_AUDIENCE", "securebank-ai-test-api")
    monkeypatch.setenv("USER_DATABASE_PATH", "/tmp/securebank-test-users.sqlite3")
    monkeypatch.setenv("SESSION_LIFETIME_SECONDS", "1200")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")
    monkeypatch.setenv("AUTH_TRUSTED_ORIGINS", "https://frontend.example.test")
    monkeypatch.setenv("LOGIN_ATTEMPT_LIMIT", "4")
    monkeypatch.setenv("LOGIN_ATTEMPT_WINDOW_SECONDS", "120")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_chunks")
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("RAG_CORPUS_PATH", "/tmp/synthetic-rag-corpus.json")
    monkeypatch.setenv("LLM_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "synthetic-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "synthetic-secret-key")
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.example.test")

    settings = Settings(_env_file=None)

    assert settings.app_name == "securebank-ai-test"
    assert settings.app_version == "9.9.9"
    assert settings.app_env == "test"
    assert settings.jwt_secret_key is not None
    assert (
        settings.jwt_secret_key.get_secret_value()
        == "test-secret-key-with-at-least-32-characters"
    )
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer == "securebank-ai-test"
    assert settings.jwt_audience == "securebank-ai-test-api"
    assert settings.user_database_path == Path("/tmp/securebank-test-users.sqlite3")
    assert settings.session_lifetime_seconds == 1200
    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "none"
    assert settings.trusted_auth_origins == frozenset({"https://frontend.example.test"})
    assert settings.login_attempt_limit == 4
    assert settings.login_attempt_window_seconds == 120
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.qdrant_collection_name == "test_chunks"
    assert settings.rag_enabled is True
    assert settings.rag_corpus_path == Path("/tmp/synthetic-rag-corpus.json")
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "synthetic-test-key"
    assert settings.llm_model == "synthetic-model"
    assert settings.llm_base_url == "https://llm.example.test/v1"
    assert settings.llm_timeout_seconds == 12.5
    assert settings.langfuse_enabled is True
    assert isinstance(settings.langfuse_public_key, SecretStr)
    assert settings.langfuse_public_key.get_secret_value() == "synthetic-public-key"
    assert isinstance(settings.langfuse_secret_key, SecretStr)
    assert settings.langfuse_secret_key.get_secret_value() == "synthetic-secret-key"
    assert str(settings.langfuse_host) == "https://langfuse.example.test/"


@pytest.mark.parametrize("timeout", ["0", "-1", "inf", "nan"])
def test_settings_reject_invalid_llm_timeout(
    monkeypatch: pytest.MonkeyPatch,
    timeout: str,
) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", timeout)

    with pytest.raises(ValueError, match="LLM timeout"):
        Settings(_env_file=None)


def test_langfuse_keys_are_optional_when_disabled() -> None:
    settings = Settings(
        _env_file=None,
        langfuse_enabled=False,
        langfuse_public_key=None,
        langfuse_secret_key=None,
    )

    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None


@pytest.mark.parametrize(
    ("public_key", "secret_key"),
    [(None, "synthetic-secret-key"), ("synthetic-public-key", None)],
)
def test_enabled_langfuse_requires_both_keys(
    public_key: str | None,
    secret_key: str | None,
) -> None:
    with pytest.raises(ValidationError, match="Langfuse public and secret keys"):
        Settings(
            _env_file=None,
            langfuse_enabled=True,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
        )


def test_langfuse_validation_error_does_not_expose_keys() -> None:
    public_key = "public-value-that-must-stay-hidden"
    secret_key = "secret-value-that-must-stay-hidden"

    with pytest.raises(ValidationError) as captured_error:
        Settings(
            _env_file=None,
            langfuse_enabled=True,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
            langfuse_host="invalid-host",
        )

    error_message = str(captured_error.value)
    assert public_key not in error_message
    assert secret_key not in error_message


def test_langfuse_keys_are_hidden_in_settings_representation() -> None:
    public_key = "public-value-that-must-stay-hidden"
    secret_key = "secret-value-that-must-stay-hidden"

    settings = Settings(
        _env_file=None,
        langfuse_enabled=True,
        langfuse_public_key=public_key,
        langfuse_secret_key=secret_key,
    )

    settings_representation = repr(settings)
    assert public_key not in settings_representation
    assert secret_key not in settings_representation
