from datetime import UTC, datetime
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import SecretStr

from app.api.dependencies import get_current_identity, get_settings
from app.api.rag import get_rag_generation_service
from app.core.config import Settings
from app.core.rag_factory import (
    RagConfigurationError,
    RagDependencyUnavailableError,
)
from app.core.rbac import Role
from app.main import app
from app.schemas.auth import AuthenticatedIdentity
from app.schemas.documents import Chunk
from app.schemas.rag_generation import RagCitation, RagGenerationResult
from app.schemas.retrieval import RetrievalResult
from app.services.llm import LLMProviderError
from app.services.qdrant import QdrantVectorStoreError
from app.services.rag_generation import (
    RagGenerationResponseError,
    RagGenerationService,
    RagPiiProtectionError,
)

JWT_SECRET = "synthetic-rag-api-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-rag-api-test"
JWT_AUDIENCE = "securebank-ai-rag-api"
VALID_EXPIRATION = datetime(2100, 1, 1, tzinfo=UTC)


class FakeRagGenerationService:
    def __init__(self, result: RagGenerationResult) -> None:
        self.result = result
        self.calls: list[tuple[str, int | None]] = []
        self.error: Exception | None = None

    def generate(
        self,
        question: str,
        top_k: int | None = None,
    ) -> RagGenerationResult:
        self.calls.append((question, top_k))
        if self.error is not None:
            raise self.error
        return self.result.model_copy(update={"question": question})


def create_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret_key=SecretStr(JWT_SECRET),
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
    )


def create_token(role: str = Role.ANALYST) -> str:
    return jwt.encode(
        {
            "sub": "synthetic-rag-api-user",
            "role": role,
            "exp": VALID_EXPIRATION,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def bearer_token(role: str = Role.ANALYST) -> str:
    return f"Bearer {create_token(role)}"


def create_result(abstained: bool = False) -> RagGenerationResult:
    chunk = Chunk(
        id="chunk-1",
        document_id="document-1",
        content="Passage réglementaire synthétique.",
        position=0,
        title="Document synthétique",
        source="synthetic://document-1",
    )
    if abstained:
        return RagGenerationResult(
            question="Question synthétique",
            answer="Les passages fournis ne permettent pas de répondre.",
            sources=[chunk],
            citations=[],
            abstained=True,
        )
    return RagGenerationResult(
        question="Question synthétique",
        answer="La règle synthétique s'applique [1].",
        sources=[chunk],
        citations=[
            RagCitation(
                reference=1,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
            )
        ],
        abstained=False,
    )


def request_rag(
    payload: object,
    *,
    authorization: str | None = None,
    service: FakeRagGenerationService | None = None,
) -> tuple[Response, FakeRagGenerationService | None]:
    def override_settings() -> Settings:
        return create_settings()

    app.dependency_overrides[get_settings] = override_settings
    if service is not None:
        app.dependency_overrides[get_rag_generation_service] = lambda: service

    headers = {"Authorization": authorization} if authorization else None
    try:
        with TestClient(app) as client:
            response = client.post("/rag/ask", json=payload, headers=headers)
        return response, service
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_rag_generation_service, None)
        app.dependency_overrides.pop(get_current_identity, None)


def test_valid_response_contains_answer_sources_citations_and_abstention() -> None:
    service = FakeRagGenerationService(create_result())

    response, _ = request_rag(
        {"question": "Quelle règle synthétique s'applique ?", "top_k": 2},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 200
    assert response.json() == {
        "question": "Quelle règle synthétique s'applique ?",
        "answer": "La règle synthétique s'applique [1].",
        "sources": [
            {
                "id": "chunk-1",
                "document_id": "document-1",
                "content": "Passage réglementaire synthétique.",
                "position": 0,
                "title": "Document synthétique",
                "source": "synthetic://document-1",
            }
        ],
        "citations": [
            {
                "reference": 1,
                "document_id": "document-1",
                "chunk_id": "chunk-1",
            }
        ],
        "abstained": False,
    }
    assert service.calls == [("Quelle règle synthétique s'applique ?", 2)]


def test_http_response_exposes_only_masked_rag_text() -> None:
    sensitive_name = "Camille Martin"
    sensitive_email = "camille.synthetic@example.test"
    chunk = Chunk(
        id="chunk-safe",
        document_id="document-safe",
        content=f"Contact {sensitive_name} via {sensitive_email}.",
        position=0,
        title=f"Dossier {sensitive_name}",
        source=f"synthetic://{sensitive_email}",
    )
    retriever = MagicMock()
    retriever.search.return_value = [RetrievalResult(chunk=chunk, score=0.8)]
    llm = MagicMock()
    llm.generate.return_value = (
        f'{{"answer":"Réponse pour {sensitive_name} [1]","abstained":false}}'
    )
    masker = MagicMock()
    masker.mask.side_effect = lambda text: text.replace(
        sensitive_name, "[PERSON]"
    ).replace(sensitive_email, "[EMAIL_ADDRESS]")
    service = RagGenerationService(retriever, llm, masker)

    response, _ = request_rag(
        {"question": f"Question de {sensitive_name}"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 200
    assert response.json()["question"] == "Question de [PERSON]"
    assert response.json()["answer"] == "Réponse pour [PERSON] [1]"
    assert response.json()["sources"][0]["content"] == (
        "Contact [PERSON] via [EMAIL_ADDRESS]."
    )
    assert response.json()["sources"][0]["title"] == "Dossier [PERSON]"
    assert response.json()["sources"][0]["source"] == ("synthetic://[EMAIL_ADDRESS]")
    assert sensitive_name not in response.text
    assert sensitive_email not in response.text


def test_abstention_is_returned_with_http_200() -> None:
    response, _ = request_rag(
        {"question": "Question sans preuve"},
        authorization=bearer_token(),
        service=FakeRagGenerationService(create_result(abstained=True)),
    )

    assert response.status_code == 200
    assert response.json()["abstained"] is True
    assert response.json()["citations"] == []


def test_missing_jwt_is_rejected() -> None:
    response, _ = request_rag(
        {"question": "Question synthétique"},
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_invalid_jwt_is_rejected() -> None:
    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization="Bearer invalid-token",
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


@pytest.mark.parametrize(
    "role",
    [Role.ANALYST, Role.COMPLIANCE_OFFICER, Role.ADMIN],
)
def test_authorized_roles_can_ask_rag(role: Role) -> None:
    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(role),
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 200


def test_unauthorized_role_is_forbidden() -> None:
    identity = AuthenticatedIdentity.model_construct(
        sub="synthetic-rag-api-user",
        role="unauthorized",
    )
    app.dependency_overrides[get_current_identity] = lambda: identity

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


@pytest.mark.parametrize(
    "question",
    ["", "   \t", "x" * 2_001],
)
def test_invalid_question_is_rejected_without_input_leak(question: str) -> None:
    response, _ = request_rag(
        {"question": question},
        authorization=bearer_token(),
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 422
    assert "input" not in response.text
    if question:
        assert question not in response.text


@pytest.mark.parametrize("top_k", [0, 6])
def test_out_of_range_top_k_is_rejected(top_k: int) -> None:
    response, _ = request_rag(
        {"question": "Question synthétique", "top_k": top_k},
        authorization=bearer_token(),
        service=FakeRagGenerationService(create_result()),
    )

    assert response.status_code == 422


def test_default_top_k_is_transmitted() -> None:
    service = FakeRagGenerationService(create_result())

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 200
    assert service.calls == [("Question synthétique", 3)]


def test_unconfigured_pipeline_returns_503() -> None:
    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "RAG pipeline is not configured"}


def test_disabled_pipeline_does_not_call_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MagicMock()
    monkeypatch.setattr("app.api.rag.rag_generation_service_provider", provider)

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
    )

    assert response.status_code == 503
    provider.get.assert_not_called()


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (RagConfigurationError("secret-key"), "RAG pipeline is not configured"),
        (RagDependencyUnavailableError("secret-host"), "RAG pipeline is unavailable"),
    ],
)
def test_enabled_pipeline_failure_returns_safe_503(
    monkeypatch: pytest.MonkeyPatch,
    error: RuntimeError,
    detail: str,
) -> None:
    enabled_settings = create_settings().model_copy(update={"rag_enabled": True})
    provider = MagicMock()
    provider.get.side_effect = error
    monkeypatch.setattr("app.api.rag.rag_generation_service_provider", provider)

    app.dependency_overrides[get_settings] = lambda: enabled_settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/rag/ask",
                json={"question": "Question synthétique"},
                headers={"Authorization": bearer_token()},
            )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
    assert response.json() == {"detail": detail}
    assert str(error) not in response.text


def test_enabled_pipeline_programming_error_is_not_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enabled_settings = create_settings().model_copy(update={"rag_enabled": True})
    provider = MagicMock()
    provider.get.side_effect = TypeError("programming defect")
    monkeypatch.setattr("app.api.rag.rag_generation_service_provider", provider)

    with pytest.raises(TypeError, match="programming defect"):
        get_rag_generation_service(enabled_settings)


def test_malformed_provider_response_returns_502_without_sensitive_data() -> None:
    sensitive_data = "raw-provider-response-with-secret"
    service = FakeRagGenerationService(create_result())
    service.error = RagGenerationResponseError(sensitive_data)

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 502
    assert sensitive_data not in response.text
    assert response.json() == {
        "detail": "The generation provider returned an invalid response"
    }


def test_provider_failure_returns_502_without_internal_details() -> None:
    sensitive_data = "provider-key-and-internal-details"
    service = FakeRagGenerationService(create_result())
    service.error = LLMProviderError(sensitive_data)

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 502
    assert sensitive_data not in response.text


def test_retrieval_failure_returns_503_without_internal_details() -> None:
    sensitive_data = "qdrant-internal-address-and-question"
    service = FakeRagGenerationService(create_result())
    service.error = QdrantVectorStoreError(sensitive_data)

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 503
    assert sensitive_data not in response.text


def test_pii_protection_failure_returns_safe_503() -> None:
    sensitive_data = "private-question-and-detector-details"
    service = FakeRagGenerationService(create_result())
    service.error = RagPiiProtectionError(sensitive_data)

    response, _ = request_rag(
        {"question": "Question synthétique"},
        authorization=bearer_token(),
        service=service,
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "PII protection is unavailable"}
    assert sensitive_data not in response.text
