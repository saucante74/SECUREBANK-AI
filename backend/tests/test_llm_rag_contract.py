import json
from collections.abc import Mapping
from dataclasses import dataclass

import httpx
import pytest
from openai import BadRequestError

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.llm import (
    SYSTEM_PROMPT,
    LLMEmptyResponseError,
    LLMProviderError,
    OpenAILLMService,
)
from app.services.rag_generation import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    RagGenerationResponseError,
    RagGenerationService,
)

MODEL_NAME = "synthetic-contract-model"
PROVIDER_SECRET = "synthetic-provider-secret"


@dataclass(frozen=True)
class FakeLLMResponse:
    output_text: object


class FakeResponsesClient:
    def __init__(
        self,
        output_text: object,
        error: Exception | None = None,
    ) -> None:
        self._response = FakeLLMResponse(output_text)
        self._error = error
        self.calls: list[dict[str, str]] = []

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
    ) -> FakeLLMResponse:
        self.calls.append(
            {
                "model": model,
                "instructions": instructions,
                "input": input,
            }
        )
        if self._error is not None:
            raise self._error
        return self._response


class FakeLLMClient:
    def __init__(self, responses: FakeResponsesClient) -> None:
        self.responses = responses


class ContractRetriever:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results
        self.calls: list[tuple[str, int]] = []

    def search(self, question: str, top_k: int = 3) -> list[RetrievalResult]:
        self.calls.append((question, top_k))
        return self._results[:top_k]


class ContractPiiMasker:
    def __init__(self, replacements: Mapping[str, str] | None = None) -> None:
        self._replacements = replacements or {}
        self.masked_texts: list[str] = []

    def mask(self, text: str) -> str:
        self.masked_texts.append(text)
        masked = text
        for original, replacement in self._replacements.items():
            masked = masked.replace(original, replacement)
        return masked


def create_provider(
    output_text: object,
    error: Exception | None = None,
) -> tuple[OpenAILLMService, FakeResponsesClient]:
    responses = FakeResponsesClient(output_text, error)
    return OpenAILLMService(FakeLLMClient(responses), MODEL_NAME), responses


def create_result(
    *,
    content: str = "Passage bancaire synthétique.",
    title: str = "Titre bancaire synthétique",
    source: str = "synthetic://llm-contract",
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id="contract-chunk",
            document_id="contract-document",
            content=content,
            position=0,
            title=title,
            source=source,
        ),
        score=0.9,
    )


def create_rag_service(
    output_text: object,
    *,
    error: Exception | None = None,
    result: RetrievalResult | None = None,
    masker: ContractPiiMasker | None = None,
) -> tuple[RagGenerationService, FakeResponsesClient]:
    provider, responses = create_provider(output_text, error)
    service = RagGenerationService(
        retriever=ContractRetriever([result or create_result()]),
        llm_service=provider,
        pii_masker=masker or ContractPiiMasker(),
    )
    return service, responses


def provider_error() -> BadRequestError:
    request = httpx.Request("POST", "https://provider.invalid/v1/responses")
    response = httpx.Response(500, request=request)
    return BadRequestError(
        PROVIDER_SECRET,
        response=response,
        body={"detail": PROVIDER_SECRET},
    )


def test_provider_transmits_responses_parameters_and_extracts_text() -> None:
    provider, responses = create_provider("Réponse synthétique")

    generated = provider.generate("Prompt synthétique")

    assert generated == "Réponse synthétique"
    assert responses.calls == [
        {
            "model": MODEL_NAME,
            "instructions": SYSTEM_PROMPT,
            "input": "Prompt synthétique",
        }
    ]


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_provider_rejects_empty_response(output_text: object) -> None:
    provider, _ = create_provider(output_text)

    with pytest.raises(LLMEmptyResponseError, match="empty response"):
        provider.generate("Prompt synthétique")


def test_provider_translates_error_without_exposing_sensitive_details() -> None:
    provider, _ = create_provider("unused", provider_error())

    with pytest.raises(LLMProviderError) as raised:
        provider.generate("Prompt synthétique")

    assert PROVIDER_SECRET not in str(raised.value)


def test_rag_accepts_provider_json_with_existing_citation() -> None:
    response = json.dumps(
        {"answer": "Réponse bancaire synthétique [1].", "abstained": False},
        ensure_ascii=False,
    )
    service, responses = create_rag_service(response)

    generated = service.generate("Question synthétique")

    assert generated.answer == "Réponse bancaire synthétique [1]."
    assert generated.abstained is False
    assert [citation.reference for citation in generated.citations] == [1]
    assert len(responses.calls) == 1


def test_rag_rejects_provider_json_with_unknown_citation() -> None:
    response = json.dumps(
        {"answer": "Réponse bancaire synthétique [2].", "abstained": False},
        ensure_ascii=False,
    )
    service, _ = create_rag_service(response)

    with pytest.raises(RagGenerationResponseError, match="unknown citation"):
        service.generate("Question synthétique")


def test_rag_rejects_malformed_provider_json_without_exposing_it() -> None:
    malformed_response = "synthetic-private-malformed-response"
    service, _ = create_rag_service(malformed_response)

    with pytest.raises(RagGenerationResponseError) as raised:
        service.generate("Question synthétique")

    assert malformed_response not in str(raised.value)


def test_rag_accepts_explicit_provider_abstention() -> None:
    response = json.dumps(
        {"answer": "Texte fournisseur synthétique.", "abstained": True},
        ensure_ascii=False,
    )
    service, _ = create_rag_service(response)

    generated = service.generate("Question synthétique")

    assert generated.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert generated.abstained is True
    assert generated.citations == []


def test_rag_propagates_empty_provider_response() -> None:
    service, _ = create_rag_service("")

    with pytest.raises(LLMEmptyResponseError, match="empty response"):
        service.generate("Question synthétique")


def test_rag_propagates_safe_provider_error() -> None:
    service, _ = create_rag_service("unused", error=provider_error())

    with pytest.raises(LLMProviderError) as raised:
        service.generate("Question synthétique")

    assert PROVIDER_SECRET not in str(raised.value)


def test_rag_masks_question_passage_and_metadata_before_provider_call() -> None:
    sensitive_question = "question.person@example.test"
    sensitive_passage = "passage.person@example.test"
    masker = ContractPiiMasker(
        {
            sensitive_question: "[EMAIL_ADDRESS]",
            sensitive_passage: "[EMAIL_ADDRESS]",
        }
    )
    response = json.dumps(
        {"answer": "Réponse synthétique [1].", "abstained": False},
        ensure_ascii=False,
    )
    result = create_result(
        content=f"Contact {sensitive_passage}.",
        title=f"Dossier {sensitive_passage}",
        source=f"synthetic://{sensitive_passage}",
    )
    service, responses = create_rag_service(response, result=result, masker=masker)

    generated = service.generate(f"Question pour {sensitive_question}")

    provider_input = responses.calls[0]["input"]
    assert sensitive_question not in provider_input
    assert sensitive_passage not in provider_input
    assert provider_input.count("[EMAIL_ADDRESS]") >= 4
    assert sensitive_question not in generated.model_dump_json()
    assert sensitive_passage not in generated.model_dump_json()


def test_rag_masks_sensitive_provider_text_in_final_answer() -> None:
    sensitive_answer = "answer.person@example.test"
    masker = ContractPiiMasker({sensitive_answer: "[EMAIL_ADDRESS]"})
    response = json.dumps(
        {"answer": f"Contact {sensitive_answer} [1].", "abstained": False},
        ensure_ascii=False,
    )
    service, _ = create_rag_service(response, masker=masker)

    generated = service.generate("Question synthétique")

    assert generated.answer == "Contact [EMAIL_ADDRESS] [1]."
    assert sensitive_answer not in generated.model_dump_json()
    assert [citation.reference for citation in generated.citations] == [1]
