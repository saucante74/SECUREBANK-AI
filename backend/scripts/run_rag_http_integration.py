import asyncio
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Protocol

import jwt
from httpx import ASGITransport, AsyncClient, Response
from pydantic import SecretStr
from qdrant_client.http.exceptions import ResponseHandlingException

from app.api.dependencies import get_settings
from app.api.rag import get_rag_generation_service
from app.core.config import Settings
from app.core.rag_factory import rag_generation_service_provider
from app.core.rbac import Role
from app.main import app
from app.schemas.rag_generation import RagGenerationResult
from app.services.qdrant import QdrantVectorStoreError
from app.services.rag_generation import RagPiiProtectionError
from scripts.run_rag_integration import (
    ANSWER_EMAIL,
    PASSAGE_EMAIL,
    QUESTION_EMAIL,
    QUESTION_MARKER,
    FakeLLM,
    IntegrationAssertionError,
    PiiControlError,
    PreparedIntegration,
    assert_absent,
    assert_positive_result,
    create_local_integration,
)

TEST_JWT_SECRET = "synthetic-http-integration-secret-with-at-least-32-characters"
TEST_JWT_ISSUER = "securebank-ai-http-integration"
TEST_JWT_AUDIENCE = "securebank-ai-http-api"
AUTHORIZED_ROLES = frozenset(
    {
        Role.ANALYST,
        Role.COMPLIANCE_OFFICER,
        Role.ADMIN,
    }
)
BASE_URL = "http://securebank-integration.test"


class RagHttpService(Protocol):
    def generate(
        self,
        question: str,
        top_k: int | None = None,
    ) -> RagGenerationResult: ...


def create_test_settings(*, rag_enabled: bool) -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret_key=SecretStr(TEST_JWT_SECRET),
        jwt_issuer=TEST_JWT_ISSUER,
        jwt_audience=TEST_JWT_AUDIENCE,
        rag_enabled=rag_enabled,
    )


def create_test_token(settings: Settings, role: Role) -> str:
    if settings.jwt_secret_key is None:
        raise ValueError("test JWT secret is unavailable")
    return jwt.encode(
        {
            "sub": "synthetic-http-integration-user",
            "role": role.value,
            "exp": datetime.now(UTC) + timedelta(minutes=10),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def authorization_headers(settings: Settings, role: Role) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_test_token(settings, role)}"}


def find_recognized_unauthorized_role() -> Role | None:
    return next((role for role in Role if role not in AUTHORIZED_ROLES), None)


@contextmanager
def dependency_override_scope(
    settings: Settings,
    service: RagHttpService | None,
) -> Iterator[None]:
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_settings] = lambda: settings
    if service is not None:
        app.dependency_overrides[get_rag_generation_service] = lambda: service
    else:
        app.dependency_overrides.pop(get_rag_generation_service, None)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


async def post_rag(
    payload: Mapping[str, object],
    settings: Settings,
    *,
    service: RagHttpService | None,
    headers: Mapping[str, str] | None = None,
) -> Response:
    with dependency_override_scope(settings, service):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
            return await client.post("/rag/ask", json=payload, headers=headers)


def parse_success_response(response: Response) -> RagGenerationResult:
    if response.status_code != 200:
        raise IntegrationAssertionError("expected HTTP 200")
    return RagGenerationResult.model_validate(response.json())


def assert_safe_error_response(response: Response, expected_status: int) -> None:
    if response.status_code != expected_status:
        raise IntegrationAssertionError("unexpected HTTP error status")
    detail = response.json().get("detail")
    if not isinstance(detail, list) or any(
        isinstance(error, dict) and "input" in error for error in detail
    ):
        raise PiiControlError("HTTP validation exposed request input")


async def run_disabled_pipeline_scenario() -> int:
    if rag_generation_service_provider._service is not None:
        raise IntegrationAssertionError("RAG provider was initialized before the test")
    settings = create_test_settings(rag_enabled=False)
    response = await post_rag(
        {"question": "Question synthétique"},
        settings,
        service=None,
        headers=authorization_headers(settings, Role.COMPLIANCE_OFFICER),
    )
    if response.status_code != 503 or response.json() != {
        "detail": "RAG pipeline is not configured"
    }:
        raise IntegrationAssertionError("disabled RAG returned an unexpected response")
    if rag_generation_service_provider._service is not None:
        raise IntegrationAssertionError("disabled RAG initialized the provider")
    return response.status_code


async def run_authentication_scenarios(
    prepared: PreparedIntegration,
    settings: Settings,
) -> tuple[int, int]:
    payload = {"question": "Question synthétique"}
    missing = await post_rag(payload, settings, service=prepared.service)
    if missing.status_code != 401 or missing.json() != {
        "detail": "Authentication required"
    }:
        raise IntegrationAssertionError("missing JWT was not rejected")
    invalid = await post_rag(
        payload,
        settings,
        service=prepared.service,
        headers={"Authorization": "Bearer invalid-token"},
    )
    if invalid.status_code != 401 or invalid.json() != {
        "detail": "Authentication required"
    }:
        raise IntegrationAssertionError("invalid JWT was not rejected")
    if prepared.llm.prompts:
        raise IntegrationAssertionError("unauthorized requests reached the RAG service")
    return missing.status_code, invalid.status_code


async def run_rag_http_scenarios(
    prepared: PreparedIntegration,
    settings: Settings,
) -> list[RagGenerationResult]:
    headers = authorization_headers(settings, Role.COMPLIANCE_OFFICER)
    factual_response = await post_rag(
        {"question": "Quel est le plafond quotidien fictif des virements en ligne ?"},
        settings,
        service=prepared.service,
        headers=headers,
    )
    factual = parse_success_response(factual_response)
    assert_positive_result(factual)
    if "25000 CHF" not in factual.answer:
        raise IntegrationAssertionError("factual HTTP answer is incomplete")

    question_response = await post_rag(
        {"question": f"Quel est le délai de traitement pour {QUESTION_EMAIL} ?"},
        settings,
        service=prepared.service,
        headers=headers,
    )
    pii_question = parse_success_response(question_response)
    assert_positive_result(pii_question)
    if QUESTION_MARKER not in pii_question.question:
        raise PiiControlError("HTTP question was not masked")
    assert_absent(QUESTION_EMAIL, [question_response.text, prepared.llm.prompts[-1]])

    passage_response = await post_rag(
        {"question": "Quelles sont les coordonnées du conseiller ?"},
        settings,
        service=prepared.service,
        headers=headers,
    )
    pii_passage = parse_success_response(passage_response)
    assert_positive_result(pii_passage)
    contact_sources = [
        source
        for source in pii_passage.sources
        if source.document_id == "integration-adviser-contact"
    ]
    if len(contact_sources) != 1:
        raise IntegrationAssertionError("expected one adviser contact source")
    contact_source = contact_sources[0]
    if not all(
        QUESTION_MARKER in value
        for value in (
            contact_source.content,
            contact_source.title,
            contact_source.source,
        )
    ):
        raise PiiControlError("HTTP source metadata was not masked")
    prompt = prepared.llm.prompts[-1]
    assert_absent(PASSAGE_EMAIL, [prompt, passage_response.text])
    assert_absent(ANSWER_EMAIL, [passage_response.text])
    if QUESTION_MARKER not in prompt or QUESTION_MARKER not in pii_passage.answer:
        raise PiiControlError("HTTP passage or answer was not masked")
    cited_references = [citation.reference for citation in pii_passage.citations]
    if any(
        f"[{reference}]" not in pii_passage.answer for reference in cited_references
    ):
        raise IntegrationAssertionError("HTTP citation changed during PII masking")

    abstention_response = await post_rag(
        {"question": "Quel est le plafond d'une carte de débit extraterrestre ?"},
        settings,
        service=prepared.service,
        headers=headers,
    )
    abstention = parse_success_response(abstention_response)
    if not abstention.abstained or abstention.citations:
        raise IntegrationAssertionError("HTTP request did not abstain")
    return [factual, pii_question, pii_passage, abstention]


async def run_validation_scenarios(
    prepared: PreparedIntegration,
    settings: Settings,
) -> list[int]:
    headers = authorization_headers(settings, Role.COMPLIANCE_OFFICER)
    sensitive_long_question = "s" * 2_001
    payloads = (
        {"question": ""},
        {"question": sensitive_long_question},
        {"question": "Question synthétique", "top_k": 0},
    )
    prompt_count = len(prepared.llm.prompts)
    statuses: list[int] = []
    for payload in payloads:
        response = await post_rag(
            payload,
            settings,
            service=prepared.service,
            headers=headers,
        )
        assert_safe_error_response(response, 422)
        assert_absent(sensitive_long_question, [response.text])
        statuses.append(response.status_code)
    if len(prepared.llm.prompts) != prompt_count:
        raise IntegrationAssertionError("invalid HTTP requests reached the RAG service")
    return statuses


def assert_complete_pii_protection(
    llm: FakeLLM,
    results: list[RagGenerationResult],
) -> None:
    sensitive_values = (QUESTION_EMAIL, PASSAGE_EMAIL, ANSWER_EMAIL)
    prompts = "\n".join(llm.prompts)
    exposed_results = "\n".join(result.model_dump_json() for result in results)
    for value in sensitive_values:
        assert_absent(value, [prompts, exposed_results])


async def run_http_integration() -> tuple[
    int,
    tuple[int, int],
    list[RagGenerationResult],
    list[int],
    int,
]:
    disabled_status = await run_disabled_pipeline_scenario()
    prepared, _, count_points = create_local_integration()
    settings = create_test_settings(rag_enabled=True)
    authentication_statuses = await run_authentication_scenarios(prepared, settings)
    results = await run_rag_http_scenarios(prepared, settings)
    validation_statuses = await run_validation_scenarios(prepared, settings)
    assert_complete_pii_protection(prepared.llm, results)
    return (
        disabled_status,
        authentication_statuses,
        results,
        validation_statuses,
        count_points(),
    )


def print_results(
    disabled_status: int,
    authentication_statuses: tuple[int, int],
    results: list[RagGenerationResult],
    validation_statuses: list[int],
    point_count: int,
) -> None:
    labels = ("A", "B", "C", "D")
    print(f"Pipeline désactivé: HTTP {disabled_status}, provider non initialisé")
    print(
        "Authentification: "
        f"sans token HTTP {authentication_statuses[0]}, "
        f"token invalide HTTP {authentication_statuses[1]}"
    )
    for label, result in zip(labels, results, strict=True):
        print(f"Scénario {label}: HTTP 200")
        print(f"  Question masquée: {result.question}")
        print(f"  Réponse masquée: {result.answer}")
        print(f"  Abstention: {result.abstained}")
        print(f"  Sources: {len(result.sources)}")
        print(f"  Citations: {len(result.citations)}")
    print(f"Validation HTTP: {validation_statuses}")
    unauthorized_role = find_recognized_unauthorized_role()
    if unauthorized_role is None:
        print("Rôle reconnu non autorisé: non applicable")
    else:
        print("Rôle reconnu non autorisé: vérifié")
    print("Prompts et JSON HTTP: PII synthétiques absentes")
    print(f"Points Qdrant: {point_count}")


def main() -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        print_results(*asyncio.run(run_http_integration()))
    except PiiControlError:
        print("Échec générique du contrôle PII HTTP.")
        return 1
    except RagPiiProtectionError:
        print("Protection PII indisponible.")
        return 1
    except IntegrationAssertionError:
        print("Échec générique d'une assertion HTTP d'intégration.")
        return 1
    except FileNotFoundError:
        print("Une ressource locale requise est indisponible.")
        return 1
    except (QdrantVectorStoreError, ResponseHandlingException):
        print("Qdrant est indisponible pour le test HTTP d'intégration.")
        return 1
    except (OSError, RuntimeError, ValueError):
        print("Le test HTTP d'intégration local n'a pas pu être exécuté.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
