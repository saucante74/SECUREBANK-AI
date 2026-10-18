from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.api.validation import SensitiveBodyRoute
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity
from app.schemas.pii import PiiMaskRequest, PiiMaskResponse
from app.services.pii_masking import PiiMasker

router = APIRouter(
    prefix="/pii",
    tags=["pii"],
    route_class=SensitiveBodyRoute,
)


@lru_cache(maxsize=1)
def get_pii_masker() -> PiiMasker:
    return PiiMasker()


@router.post("/mask", response_model=PiiMaskResponse)
def mask_pii(
    request: PiiMaskRequest,
    _identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.COMPLIANCE_OFFICER,
                Role.ADMIN,
            )
        ),
    ],
    masker: Annotated[PiiMasker, Depends(get_pii_masker)],
) -> PiiMaskResponse:
    return PiiMaskResponse(masked_text=masker.mask(request.text))
