from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.api.dependencies import require_roles
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity
from app.schemas.pii import PiiMaskRequest, PiiMaskResponse
from app.services.pii_masking import PiiMasker


class SensitiveBodyRoute(APIRoute):
    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def sanitized_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError as error:
                sanitized_errors = [
                    {
                        key: validation_error[key]
                        for key in ("type", "loc", "msg")
                        if key in validation_error
                    }
                    for validation_error in error.errors()
                ]
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=sanitized_errors,
                ) from None

        return sanitized_route_handler


router = APIRouter(
    prefix="/pii",
    tags=["pii"],
    route_class=SensitiveBodyRoute,
)
pii_masker = PiiMasker()


def get_pii_masker() -> PiiMasker:
    return pii_masker


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
