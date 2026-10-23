from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.schemas.documents import Chunk
from app.services.llm import LLMGeneration, LLMProviderError
from app.services.rag_generation import RagGenerationResponseError, build_rag_prompt
from scripts.run_openai_smoke_test import ALLOW_REAL_CALL_FLAG
from scripts.run_rag_integration import CORPUS_PATH
from scripts.run_rag_openai_integration import (
    EXPECTED_DOCUMENT_IDS,
    OPENAI_INTEGRATION_COLLECTION_NAME,
    IntegrationSafetyError,
    PreflightLLMService,
    load_authorized_corpus,
    main,
    reset_openai_integration_collection,
)


class FakeLLM:
    def __init__(
        self,
        response: str = '{"answer":"Réponse [1].","abstained":false}',
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> LLMGeneration:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return LLMGeneration(text=self.response)


def make_settings(api_key: str | None = "synthetic-rag-openai-key") -> Settings:
    return Settings(
        _env_file=None,
        llm_api_key=SecretStr(api_key) if api_key is not None else None,
    )


def make_chunk() -> Chunk:
    return Chunk(
        id="authorized-chunk",
        document_id=next(iter(EXPECTED_DOCUMENT_IDS)),
        content="Contenu synthétique sans donnée personnelle.",
        position=0,
        title="Titre synthétique",
        source="synthetic://authorized",
    )


def make_guard(delegate: FakeLLM, max_calls: int = 2) -> PreflightLLMService:
    chunk = make_chunk()
    return PreflightLLMService(
        delegate=delegate,
        allowed_document_ids=frozenset({chunk.document_id}),
        allowed_chunk_ids=frozenset({chunk.id}),
        forbidden_values=("private.synthetic@example.com",),
        max_calls=max_calls,
    )


def test_default_mode_initializes_nothing(capsys: Any) -> None:
    settings_factory = Mock(side_effect=AssertionError("settings must not load"))
    integration_factory = Mock(side_effect=AssertionError("pipeline must not load"))

    exit_code = main(
        [],
        settings_factory=settings_factory,
        integration_factory=integration_factory,
    )

    assert exit_code == 0
    settings_factory.assert_not_called()
    integration_factory.assert_not_called()
    assert "disabled" in capsys.readouterr().out


def test_preflight_limits_provider_calls() -> None:
    delegate = FakeLLM()
    guard = make_guard(delegate, max_calls=1)
    prompt = build_rag_prompt("Question synthétique", [make_chunk()])

    guard.generate(prompt)
    with pytest.raises(IntegrationSafetyError, match="budget"):
        guard.generate(prompt)

    assert len(delegate.prompts) == 1
    assert guard.call_count == 1


def test_preflight_rejects_pii_before_provider_call() -> None:
    delegate = FakeLLM()
    guard = make_guard(delegate)
    chunk = make_chunk().model_copy(update={"content": "private.synthetic@example.com"})
    prompt = build_rag_prompt("Question synthétique", [chunk])

    with pytest.raises(IntegrationSafetyError, match="PII"):
        guard.generate(prompt)

    assert delegate.prompts == []
    assert guard.call_count == 0


def test_preflight_rejects_passage_outside_authorized_corpus() -> None:
    delegate = FakeLLM()
    guard = make_guard(delegate)
    chunk = make_chunk().model_copy(update={"document_id": "foreign-document"})
    prompt = build_rag_prompt("Question synthétique", [chunk])

    with pytest.raises(IntegrationSafetyError, match="Unauthorized passage"):
        guard.generate(prompt)

    assert delegate.prompts == []


def test_corpus_loader_rejects_unexpected_path(tmp_path: Path) -> None:
    unexpected_path = tmp_path / "corpus.json"
    unexpected_path.write_text('{"documents": []}', encoding="utf-8")

    with pytest.raises(IntegrationSafetyError, match="path"):
        load_authorized_corpus(unexpected_path)


def test_corpus_loader_accepts_only_pinned_synthetic_corpus() -> None:
    corpus = load_authorized_corpus(CORPUS_PATH)

    assert {document.id for document in corpus.documents} == EXPECTED_DOCUMENT_IDS


def test_collection_reset_rejects_foreign_collection() -> None:
    client = Mock()

    with pytest.raises(IntegrationSafetyError, match="foreign collection"):
        reset_openai_integration_collection(client, "securebank_chunks")

    client.collection_exists.assert_not_called()
    client.delete_collection.assert_not_called()


def test_collection_reset_targets_only_reserved_collection() -> None:
    client = Mock()
    client.collection_exists.return_value = True

    reset_openai_integration_collection(
        client,
        OPENAI_INTEGRATION_COLLECTION_NAME,
    )

    client.collection_exists.assert_called_once_with(OPENAI_INTEGRATION_COLLECTION_NAME)
    client.delete_collection.assert_called_once_with(
        collection_name=OPENAI_INTEGRATION_COLLECTION_NAME
    )


@pytest.mark.parametrize(
    "error",
    [
        RagGenerationResponseError("invalid response with synthetic-rag-openai-key"),
        LLMProviderError("provider error with synthetic-rag-openai-key"),
    ],
)
def test_authorized_mode_hides_generation_errors(
    error: Exception,
    capsys: Any,
) -> None:
    integration_factory = Mock(side_effect=error)

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=make_settings,
        integration_factory=integration_factory,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    integration_factory.assert_called_once()
    assert output == "OpenAI RAG integration failed.\n"
    assert "synthetic-rag-openai-key" not in output


def test_authorized_mode_rejects_missing_key_before_pipeline(capsys: Any) -> None:
    integration_factory = Mock(side_effect=AssertionError("pipeline must not load"))

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=lambda: make_settings(None),
        integration_factory=integration_factory,
    )

    assert exit_code == 1
    integration_factory.assert_not_called()
    assert capsys.readouterr().out == "OpenAI RAG integration failed.\n"
