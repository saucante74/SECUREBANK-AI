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

    settings = Settings(_env_file=None)

    assert settings.app_name == "securebank-ai"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.jwt_secret_key is None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer is None
    assert settings.jwt_audience is None


def test_settings_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "securebank-ai-test")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ISSUER", "securebank-ai-test")
    monkeypatch.setenv("JWT_AUDIENCE", "securebank-ai-test-api")

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
