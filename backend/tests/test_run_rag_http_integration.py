import asyncio
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from app.api.dependencies import get_settings
from app.core.jwt import validate_jwt
from app.core.rbac import Role
from app.main import app
from app.schemas.documents import Chunk
from app.schemas.rag_generation import RagCitation, RagGenerationResult
from scripts.run_rag_http_integration import (
    authorization_headers,
    create_test_settings,
    create_test_token,
    dependency_override_scope,
    find_recognized_unauthorized_role,
    post_rag,
)


class FakeHttpRagService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    def generate(
        self,
        question: str,
        top_k: int | None = None,
    ) -> RagGenerationResult:
        self.calls.append((question, top_k))
        chunk = Chunk(
            id="synthetic-chunk",
            document_id="synthetic-document",
            content="Contenu synthétique.",
            position=0,
            title="Titre synthétique",
            source="synthetic://http-test",
        )
        return RagGenerationResult(
            question=question,
            answer="Réponse synthétique [1].",
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


@contextmanager
def preserve_overrides() -> Iterator[None]:
    previous = app.dependency_overrides.copy()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_test_token_is_accepted_by_real_jwt_validation() -> None:
    settings = create_test_settings(rag_enabled=True)

    payload = validate_jwt(
        create_test_token(settings, Role.COMPLIANCE_OFFICER),
        settings,
    )

    assert payload["sub"] == "synthetic-http-integration-user"
    assert payload["role"] == Role.COMPLIANCE_OFFICER


def test_dependency_overrides_restore_previous_state_after_error() -> None:
    settings = create_test_settings(rag_enabled=True)

    def previous_override() -> object:
        return settings

    with preserve_overrides():
        app.dependency_overrides[get_settings] = previous_override
        with pytest.raises(RuntimeError, match="synthetic failure"):
            with dependency_override_scope(settings, FakeHttpRagService()):
                raise RuntimeError("synthetic failure")
        assert app.dependency_overrides == {get_settings: previous_override}


def test_post_rag_uses_real_jwt_and_rbac_with_injected_service() -> None:
    settings = create_test_settings(rag_enabled=True)
    service = FakeHttpRagService()

    response = asyncio.run(
        post_rag(
            {"question": "Question HTTP synthétique", "top_k": 2},
            settings,
            service=service,
            headers=authorization_headers(settings, Role.COMPLIANCE_OFFICER),
        )
    )

    assert response.status_code == 200
    assert RagGenerationResult.model_validate(response.json()).answer == (
        "Réponse synthétique [1]."
    )
    assert service.calls == [("Question HTTP synthétique", 2)]


def test_invalid_http_payload_does_not_call_injected_service() -> None:
    settings = create_test_settings(rag_enabled=True)
    service = FakeHttpRagService()

    response = asyncio.run(
        post_rag(
            {"question": "", "top_k": 0},
            settings,
            service=service,
            headers=authorization_headers(settings, Role.ANALYST),
        )
    )

    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])
    assert service.calls == []


def test_all_recognized_roles_are_authorized_for_rag() -> None:
    assert find_recognized_unauthorized_role() is None
