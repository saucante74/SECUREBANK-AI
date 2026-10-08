from typing import Annotated, Never

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, settings
from app.core.jwt import JWTValidationError, validate_jwt
from app.schemas.auth import AuthenticatedIdentity

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return settings


def get_current_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()

    try:
        payload = validate_jwt(credentials.credentials, app_settings)
    except JWTValidationError:
        raise_unauthorized()

    return AuthenticatedIdentity(sub=str(payload["sub"]))


def raise_unauthorized() -> Never:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
