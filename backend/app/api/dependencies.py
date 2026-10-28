from collections.abc import Callable
from typing import Annotated, Never

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, settings
from app.core.jwt import JWTValidationError, validate_jwt
from app.core.passwords import PasswordHasher
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity
from app.services.authentication import AuthenticationService
from app.services.sessions import SQLiteSessionRepository
from app.services.users import SQLiteUserRepository

SESSION_COOKIE_NAME = "securebank_session"
CSRF_COOKIE_NAME = "securebank_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return settings


def get_user_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> SQLiteUserRepository:
    repository = SQLiteUserRepository(app_settings.user_database_path)
    repository.initialize()
    return repository


def get_session_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
    _users: Annotated[SQLiteUserRepository, Depends(get_user_repository)],
) -> SQLiteSessionRepository:
    repository = SQLiteSessionRepository(app_settings.user_database_path)
    repository.initialize()
    return repository


def get_authentication_service(
    app_settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[SQLiteUserRepository, Depends(get_user_repository)],
    sessions: Annotated[SQLiteSessionRepository, Depends(get_session_repository)],
) -> AuthenticationService:
    return AuthenticationService(
        users,
        sessions,
        PasswordHasher(),
        app_settings.session_lifetime_seconds,
        app_settings.login_attempt_limit,
        app_settings.login_attempt_window_seconds,
    )


def get_current_identity(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedIdentity:
    if credentials is not None:
        if credentials.scheme.lower() != "bearer":
            raise_unauthorized()
        return identity_from_bearer(credentials.credentials, app_settings)

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise_unauthorized()
    users = SQLiteUserRepository(app_settings.user_database_path)
    users.initialize()
    sessions = SQLiteSessionRepository(app_settings.user_database_path)
    sessions.initialize()
    identity = sessions.resolve(session_token)
    if identity is None:
        raise_unauthorized()
    if request.method not in SAFE_HTTP_METHODS:
        validate_csrf(request, sessions, session_token)
    return identity


def identity_from_bearer(token: str, app_settings: Settings) -> AuthenticatedIdentity:
    try:
        payload = validate_jwt(token, app_settings)
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


def validate_csrf(
    request: Request,
    sessions: SQLiteSessionRepository,
    session_token: str,
) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if (
        not cookie_token
        or not header_token
        or cookie_token != header_token
        or not sessions.validate_csrf(session_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


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
