from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    get_authentication_service,
    get_current_identity,
    get_session_repository,
    get_settings,
    require_roles,
)
from app.core.config import Settings
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity, LoginRequest
from app.services.authentication import (
    AuthenticationService,
    InvalidCredentialsError,
    LoginRateLimitError,
)
from app.services.sessions import SQLiteSessionRepository

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=AuthenticatedIdentity)
def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    app_settings: Annotated[Settings, Depends(get_settings)],
    authentication: Annotated[
        AuthenticationService,
        Depends(get_authentication_service),
    ],
) -> AuthenticatedIdentity:
    validate_login_origin(request, app_settings)
    try:
        result = authentication.login(
            credentials.username,
            credentials.password.get_secret_value(),
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from None
    except LoginRateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
        ) from None

    cookie_options = {
        "secure": app_settings.session_cookie_secure,
        "samesite": app_settings.session_cookie_samesite,
        "max_age": app_settings.session_lifetime_seconds,
        "path": "/",
    }
    response.set_cookie(
        SESSION_COOKIE_NAME,
        result.session.session_token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        result.session.csrf_token,
        httponly=False,
        **cookie_options,
    )
    return result.identity


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    _identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    sessions: Annotated[SQLiteSessionRepository, Depends(get_session_repository)],
) -> None:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        sessions.delete(session_token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


@router.get("/me", response_model=AuthenticatedIdentity)
def read_authenticated_identity(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> AuthenticatedIdentity:
    return identity


@router.get("/analyst")
def read_analyst_access(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.COMPLIANCE_OFFICER,
                Role.ADMIN,
            ),
        ),
    ],
) -> dict[str, str]:
    return {"access": "granted", "role": identity.role}


@router.get("/admin")
def read_admin_access(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(require_roles(Role.ADMIN)),
    ],
) -> dict[str, str]:
    return {"access": "granted", "role": identity.role}


def validate_login_origin(request: Request, app_settings: Settings) -> None:
    origin = request.headers.get("Origin")
    request_origin = f"{request.url.scheme}://{request.url.netloc}"
    if origin != request_origin and origin not in app_settings.trusted_auth_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed",
        )
