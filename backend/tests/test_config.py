from pathlib import Path

import pytest

from app.core.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_ALGORITHM", raising=False)
    monkeypatch.delenv("JWT_ISSUER", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_COLLECTION_NAME", raising=False)
    monkeypatch.delenv("RAG_ENABLED", raising=False)
    monkeypatch.delenv("RAG_CORPUS_PATH", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "securebank-ai"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.jwt_secret_key is None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer is None
    assert settings.jwt_audience is None
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_name == "securebank_chunks"
    assert settings.rag_enabled is False
    assert settings.rag_corpus_path is None
    assert settings.llm_api_key is None
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.llm_base_url is None
    assert settings.llm_timeout_seconds == 30.0


def test_settings_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "securebank-ai-test")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ISSUER", "securebank-ai-test")
    monkeypatch.setenv("JWT_AUDIENCE", "securebank-ai-test-api")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_chunks")
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("RAG_CORPUS_PATH", "/tmp/synthetic-rag-corpus.json")
    monkeypatch.setenv("LLM_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")

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
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.qdrant_collection_name == "test_chunks"
    assert settings.rag_enabled is True
    assert settings.rag_corpus_path == Path("/tmp/synthetic-rag-corpus.json")
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "synthetic-test-key"
    assert settings.llm_model == "synthetic-model"
    assert settings.llm_base_url == "https://llm.example.test/v1"
    assert settings.llm_timeout_seconds == 12.5


@pytest.mark.parametrize("timeout", ["0", "-1", "inf", "nan"])
def test_settings_reject_invalid_llm_timeout(
    monkeypatch: pytest.MonkeyPatch,
    timeout: str,
) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", timeout)

    with pytest.raises(ValueError, match="LLM timeout"):
        Settings(_env_file=None)
