import asyncio
from datetime import UTC, datetime

import jwt
from httpx import ASGITransport, AsyncClient, Response

from app.api.dependencies import get_settings
from app.core.config import Settings
from app.main import app

JWT_SECRET = "synthetic-auth-secret-key-with-at-least-32-characters"
WRONG_SECRET = "different-auth-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-auth-test"
JWT_AUDIENCE = "securebank-ai-auth-api"
VALID_EXPIRATION = datetime(2100, 1, 1, tzinfo=UTC)
EXPIRED_AT = datetime(2000, 1, 1, tzinfo=UTC)


def create_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret_key=JWT_SECRET,
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
    )


def create_token(
    *,
    secret: str = JWT_SECRET,
    expiration: datetime = VALID_EXPIRATION,
    subject: str | None = "synthetic-user",
) -> str:
    payload: dict[str, object] = {
        "exp": expiration,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    if subject is not None:
        payload["sub"] = subject
    return jwt.encode(payload, secret, algorithm="HS256")


def request_auth_me(
    settings: Settings,
    authorization: str | None = None,
) -> Response:
    def override_settings() -> Settings:
        return settings

    async def send_request() -> Response:
        transport = ASGITransport(app=app)
        headers = {"Authorization": authorization} if authorization else None
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/auth/me", headers=headers)

    app.dependency_overrides[get_settings] = override_settings
    try:
        return asyncio.run(send_request())
    finally:
        app.dependency_overrides.pop(get_settings)


def assert_unauthorized(response: Response) -> None:
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_auth_me_with_valid_token() -> None:
    response = request_auth_me(
        create_settings(),
        f"Bearer {create_token()}",
    )

    assert response.status_code == 200
    assert response.json() == {"sub": "synthetic-user"}


def test_auth_me_without_authorization() -> None:
    assert_unauthorized(request_auth_me(create_settings()))


def test_auth_me_with_wrong_scheme() -> None:
    assert_unauthorized(
        request_auth_me(create_settings(), f"Basic {create_token()}"),
    )


def test_auth_me_with_malformed_token() -> None:
    assert_unauthorized(request_auth_me(create_settings(), "Bearer malformed-token"))


def test_auth_me_with_invalid_signature() -> None:
    token = create_token(secret=WRONG_SECRET)

    assert_unauthorized(request_auth_me(create_settings(), f"Bearer {token}"))


def test_auth_me_with_expired_token() -> None:
    token = create_token(expiration=EXPIRED_AT)

    assert_unauthorized(request_auth_me(create_settings(), f"Bearer {token}"))


def test_auth_me_without_subject() -> None:
    token = create_token(subject=None)

    assert_unauthorized(request_auth_me(create_settings(), f"Bearer {token}"))


def test_auth_me_with_empty_subject() -> None:
    token = create_token(subject="")

    assert_unauthorized(request_auth_me(create_settings(), f"Bearer {token}"))


def test_auth_me_without_jwt_configuration() -> None:
    token = create_token()

    assert_unauthorized(
        request_auth_me(Settings(_env_file=None), f"Bearer {token}"),
    )


def test_health_remains_public() -> None:
    async def request_health() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "securebank-ai",
        "version": "0.1.0",
    }
