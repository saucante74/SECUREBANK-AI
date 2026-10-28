from datetime import UTC, datetime

import jwt
from pydantic import SecretStr

from app.core.config import Settings
from app.core.rbac import Role
from scripts.generate_development_jwt import (
    TOKEN_LIFETIME,
    TOKEN_SUBJECT,
    generate_development_token,
)

TEST_SECRET = "synthetic-development-secret-with-at-least-32-characters"
TEST_ISSUER = "securebank-ai-development-test"
TEST_AUDIENCE = "securebank-ai-development-api"


def test_generated_token_uses_backend_configuration_and_expires_in_15_minutes() -> None:
    issued_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    settings = Settings(
        _env_file=None,
        jwt_secret_key=SecretStr(TEST_SECRET),
        jwt_issuer=TEST_ISSUER,
        jwt_audience=TEST_AUDIENCE,
    )

    token = generate_development_token(settings, issued_at)
    payload = jwt.decode(
        token,
        TEST_SECRET,
        algorithms=[settings.jwt_algorithm],
        audience=TEST_AUDIENCE,
        issuer=TEST_ISSUER,
        options={"verify_exp": False},
    )

    assert payload["sub"] == TOKEN_SUBJECT
    assert payload["role"] == Role.ANALYST.value
    assert payload["iat"] == int(issued_at.timestamp())
    assert payload["exp"] - payload["iat"] == int(TOKEN_LIFETIME.total_seconds())
