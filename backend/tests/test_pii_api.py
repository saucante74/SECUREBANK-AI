import asyncio
from datetime import UTC, datetime

import jwt
from httpx import ASGITransport, AsyncClient, Response
from pydantic import SecretStr

from app.api.dependencies import get_settings
from app.core.config import Settings
from app.core.rbac import Role
from app.main import app

JWT_SECRET = "synthetic-pii-api-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-pii-api-test"
JWT_AUDIENCE = "securebank-ai-pii-api"
VALID_EXPIRATION = datetime(2100, 1, 1, tzinfo=UTC)
EXPIRED_AT = datetime(2000, 1, 1, tzinfo=UTC)


def create_settings() -> Settings:
    return Settings(
        jwt_secret_key=SecretStr(JWT_SECRET),
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
    )


def create_token(
    *,
    role: str = Role.ANALYST,
    expiration: datetime = VALID_EXPIRATION,
) -> str:
    return jwt.encode(
        {
            "sub": "synthetic-pii-api-user",
            "role": role,
            "exp": expiration,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def request_mask(
    payload: object,
    authorization: str | None = None,
) -> Response:
    def override_settings() -> Settings:
        return create_settings()

    async def send_request() -> Response:
        transport = ASGITransport(app=app)
        headers = {"Authorization": authorization} if authorization else None
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/pii/mask", json=payload, headers=headers)

    app.dependency_overrides[get_settings] = override_settings
    try:
        return asyncio.run(send_request())
    finally:
        app.dependency_overrides.pop(get_settings)


def bearer_token(
    role: str = Role.ANALYST,
    expiration: datetime = VALID_EXPIRATION,
) -> str:
    return f"Bearer {create_token(role=role, expiration=expiration)}"


def assert_unauthorized(response: Response) -> None:
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_analyst_can_mask_pii() -> None:
    response = request_mask(
        {"text": "Contact : alice.dupont@example.com."},
        bearer_token(Role.ANALYST),
    )

    assert response.status_code == 200
    assert response.json() == {"masked_text": "Contact : [EMAIL_ADDRESS]."}


def test_compliance_officer_can_mask_pii() -> None:
    response = request_mask(
        {"text": "Contact : alice.dupont@example.com."},
        bearer_token(Role.COMPLIANCE_OFFICER),
    )

    assert response.status_code == 200


def test_admin_can_mask_pii() -> None:
    response = request_mask(
        {"text": "Contact : alice.dupont@example.com."},
        bearer_token(Role.ADMIN),
    )

    assert response.status_code == 200


def test_missing_token_is_rejected() -> None:
    assert_unauthorized(request_mask({"text": "Texte synthétique."}))


def test_invalid_token_is_rejected() -> None:
    assert_unauthorized(
        request_mask({"text": "Texte synthétique."}, "Bearer invalid-token")
    )


def test_expired_token_is_rejected() -> None:
    assert_unauthorized(
        request_mask(
            {"text": "Texte synthétique."},
            bearer_token(expiration=EXPIRED_AT),
        )
    )


def test_unknown_role_is_rejected() -> None:
    assert_unauthorized(
        request_mask(
            {"text": "Texte synthétique."},
            bearer_token("unknown"),
        )
    )


def test_masks_phone_number() -> None:
    response = request_mask(
        {"text": "Téléphone : +33 6 12 34 56 78."},
        bearer_token(),
    )

    assert response.json() == {"masked_text": "Téléphone : [PHONE_NUMBER]."}


def test_masks_synthetic_iban() -> None:
    response = request_mask(
        {"text": "IBAN fictif : CH93 0076 2011 6238 5295 7."},
        bearer_token(),
    )

    assert response.json() == {"masked_text": "IBAN fictif : [IBAN_CODE]."}


def test_masks_person_name() -> None:
    response = request_mask(
        {"text": "La cliente fictive s'appelle Camille Martin."},
        bearer_token(),
    )

    assert response.json() == {"masked_text": "La cliente fictive s'appelle [PERSON]."}


def test_masks_multiple_pii_without_exposing_original_values() -> None:
    original_values = (
        "Camille Martin",
        "alice.dupont@example.com",
        "+33 6 12 34 56 78",
        "CH93 0076 2011 6238 5295 7",
    )
    text = f"{original_values[0]} utilise {original_values[1]}, "
    text += f"{original_values[2]} et {original_values[3]}."

    response = request_mask({"text": text}, bearer_token())

    assert response.status_code == 200
    assert response.json() == {
        "masked_text": (
            "[PERSON] utilise [EMAIL_ADDRESS], [PHONE_NUMBER] et [IBAN_CODE]."
        )
    }
    assert set(response.json()) == {"masked_text"}
    assert all(value not in response.text for value in original_values)


def test_text_without_pii_is_unchanged() -> None:
    text = "Le contrôle synthétique est terminé."

    response = request_mask({"text": text}, bearer_token())

    assert response.json() == {"masked_text": text}


def test_empty_text_is_rejected_without_input_leak() -> None:
    response = request_mask({"text": ""}, bearer_token())

    assert response.status_code == 422
    assert "input" not in response.text


def test_whitespace_text_is_rejected_without_input_leak() -> None:
    text = "   \t  "

    response = request_mask({"text": text}, bearer_token())

    assert response.status_code == 422
    assert text not in response.text
    assert "input" not in response.text


def test_oversized_text_is_rejected_without_input_leak() -> None:
    text = "alice.dupont@example.com" + "x" * 10_000

    response = request_mask({"text": text}, bearer_token())

    assert response.status_code == 422
    assert "alice.dupont@example.com" not in response.text
    assert "input" not in response.text


def test_incorrect_text_type_is_rejected_without_input_leak() -> None:
    sensitive_value = "alice.dupont@example.com"

    response = request_mask(
        {"text": {"submitted_value": sensitive_value}},
        bearer_token(),
    )

    assert response.status_code == 422
    assert sensitive_value not in response.text
    assert "submitted_value" not in response.text
    assert "input" not in response.text


def test_health_remains_public() -> None:
    async def request_health() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
