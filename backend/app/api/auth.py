from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_identity, require_roles
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity

router = APIRouter(prefix="/auth", tags=["authentication"])


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
