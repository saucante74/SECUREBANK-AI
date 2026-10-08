from datetime import UTC, datetime

import jwt
import pytest

from app.core.config import Settings
from app.core.jwt import JWTValidationError, validate_jwt

JWT_SECRET = "synthetic-test-secret-key-with-at-least-32-characters"
WRONG_SECRET = "different-synthetic-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-test"
JWT_AUDIENCE = "securebank-ai-test-api"
VALID_EXPIRATION = datetime(2100, 1, 1, tzinfo=UTC)
EXPIRED_AT = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture
def jwt_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret_key=JWT_SECRET,
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
    )


def create_token(
    *,
    secret: str = JWT_SECRET,
    algorithm: str = "HS256",
    expiration: datetime | None = VALID_EXPIRATION,
    issuer: str | None = JWT_ISSUER,
    audience: str | None = JWT_AUDIENCE,
) -> str:
    payload: dict[str, object] = {"sub": "synthetic-user"}
    if expiration is not None:
        payload["exp"] = expiration
    if issuer is not None:
        payload["iss"] = issuer
    if audience is not None:
        payload["aud"] = audience
    return jwt.encode(payload, secret, algorithm=algorithm)


def assert_rejected(token: str, settings: Settings) -> None:
    with pytest.raises(JWTValidationError, match="JWT validation failed"):
        validate_jwt(token, settings)


def test_valid_token(jwt_settings: Settings) -> None:
    payload = validate_jwt(create_token(), jwt_settings)

    assert payload["sub"] == "synthetic-user"
    assert payload["iss"] == JWT_ISSUER
    assert payload["aud"] == JWT_AUDIENCE


def test_invalid_signature(jwt_settings: Settings) -> None:
    assert_rejected(create_token(secret=WRONG_SECRET), jwt_settings)


def test_expired_token(jwt_settings: Settings) -> None:
    assert_rejected(create_token(expiration=EXPIRED_AT), jwt_settings)


def test_wrong_issuer(jwt_settings: Settings) -> None:
    assert_rejected(create_token(issuer="unexpected-issuer"), jwt_settings)


def test_wrong_audience(jwt_settings: Settings) -> None:
    assert_rejected(create_token(audience="unexpected-audience"), jwt_settings)


def test_disallowed_algorithm(jwt_settings: Settings) -> None:
    assert_rejected(create_token(algorithm="HS384"), jwt_settings)


def test_malformed_token(jwt_settings: Settings) -> None:
    assert_rejected("malformed-token", jwt_settings)


def test_missing_expiration(jwt_settings: Settings) -> None:
    assert_rejected(create_token(expiration=None), jwt_settings)


def test_missing_issuer(jwt_settings: Settings) -> None:
    assert_rejected(create_token(issuer=None), jwt_settings)


def test_missing_audience(jwt_settings: Settings) -> None:
    assert_rejected(create_token(audience=None), jwt_settings)


def test_missing_jwt_configuration() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(JWTValidationError, match="JWT configuration is unavailable"):
        validate_jwt(create_token(), settings)
