from typing import cast

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings


class JWTValidationError(Exception):
    pass


def validate_jwt(token: str, settings: Settings) -> dict[str, object]:
    if (
        settings.jwt_secret_key is None
        or settings.jwt_issuer is None
        or settings.jwt_audience is None
    ):
        raise JWTValidationError("JWT configuration is unavailable")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except InvalidTokenError as error:
        raise JWTValidationError("JWT validation failed") from error

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise JWTValidationError("JWT validation failed")

    payload["sub"] = subject.strip()
    return cast(dict[str, object], payload)
