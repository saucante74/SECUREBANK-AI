from collections.abc import Callable
from typing import Annotated, Never

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, settings
from app.core.jwt import JWTValidationError, validate_jwt
from app.core.rbac import Role
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

    role_claim = payload.get("role")
    if not isinstance(role_claim, str) or not role_claim.strip():
        raise_unauthorized()

    try:
        role = Role(role_claim)
    except ValueError:
        raise_unauthorized()

    return AuthenticatedIdentity(sub=str(payload["sub"]), role=role)


def require_roles(
    *allowed_roles: Role,
) -> Callable[[AuthenticatedIdentity], AuthenticatedIdentity]:
    allowed_role_set = frozenset(allowed_roles)

    def authorize_role(
        identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    ) -> AuthenticatedIdentity:
        if identity.role not in allowed_role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return identity

    return authorize_role


def raise_unauthorized() -> Never:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
