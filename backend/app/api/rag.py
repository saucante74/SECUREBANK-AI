from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_settings, require_roles
from app.api.validation import SensitiveBodyRoute
from app.core.config import Settings
from app.core.rag_factory import (
    RagConfigurationError,
    RagDependencyUnavailableError,
    rag_generation_service_provider,
)
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity
from app.schemas.rag_generation import RagAskRequest, RagGenerationResult
from app.services.llm import LLMServiceError
from app.services.qdrant import QdrantVectorStoreError
from app.services.rag_generation import (
    RagGenerationResponseError,
    RagGenerationService,
)

router = APIRouter(
    prefix="/rag",
    tags=["rag"],
    route_class=SensitiveBodyRoute,
)


def get_rag_generation_service(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> RagGenerationService:
    if not app_settings.rag_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is not configured",
        )
    try:
        return rag_generation_service_provider.get(app_settings)
    except RagConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is not configured",
        ) from None
    except RagDependencyUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is unavailable",
        ) from None


@router.post("/ask", response_model=RagGenerationResult)
def ask_rag(
    request: RagAskRequest,
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
    service: Annotated[RagGenerationService, Depends(get_rag_generation_service)],
) -> RagGenerationResult:
    try:
        return service.generate(request.question, top_k=request.top_k)
    except RagGenerationResponseError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The generation provider returned an invalid response",
        ) from None
    except LLMServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The generation provider is unavailable",
        ) from None
    except QdrantVectorStoreError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The RAG pipeline is unavailable",
        ) from None
