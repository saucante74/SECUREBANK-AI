from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_identity
from app.schemas.auth import AuthenticatedIdentity

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=AuthenticatedIdentity)
def read_authenticated_identity(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> AuthenticatedIdentity:
    return identity
