import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import APIConnectionError, BadRequestError

from app.services.llm import (
    SYSTEM_PROMPT,
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMProviderError,
    OpenAILLMService,
)

API_KEY = "synthetic-secret-api-key"


def create_client(output_text: object = "Réponse synthétique") -> MagicMock:
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(output_text=output_text)
    return client


def test_successful_generation_returns_text() -> None:
    service = OpenAILLMService(create_client(), "synthetic-model")

    result = service.generate("Question synthétique")

    assert result == "Réponse synthétique"


def test_generation_transmits_prompt_model_and_system_prompt() -> None:
    client = create_client()
    service = OpenAILLMService(client, "configured-model")

    service.generate("Prompt utilisateur")

    client.responses.create.assert_called_once_with(
        model="configured-model",
        instructions=SYSTEM_PROMPT,
        input="Prompt utilisateur",
    )


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_empty_response_is_rejected(output_text: object) -> None:
    service = OpenAILLMService(create_client(output_text), "synthetic-model")

    with pytest.raises(LLMEmptyResponseError, match="empty response"):
        service.generate("Question synthétique")


@pytest.mark.parametrize("prompt", ["", "   \t", None, 42])
def test_empty_or_invalid_prompt_is_rejected(prompt: object) -> None:
    client = create_client()
    service = OpenAILLMService(client, "synthetic-model")

    with pytest.raises(ValueError, match="prompt must contain"):
        service.generate(prompt)

    client.responses.create.assert_not_called()


def test_network_error_is_translated() -> None:
    client = create_client()
    request = httpx.Request("POST", "https://llm.example.test/v1/responses")
    client.responses.create.side_effect = APIConnectionError(request=request)

    with pytest.raises(LLMConnectionError, match="Unable to reach"):
        OpenAILLMService(client, "synthetic-model").generate("Question synthétique")


def test_api_error_is_translated() -> None:
    client = create_client()
    request = httpx.Request("POST", "https://llm.example.test/v1/responses")
    response = httpx.Response(400, request=request)
    client.responses.create.side_effect = BadRequestError(
        "Synthetic provider error",
        response=response,
        body=None,
    )

    with pytest.raises(LLMProviderError, match="rejected the request"):
        OpenAILLMService(client, "synthetic-model").generate("Question synthétique")


@pytest.mark.parametrize("error_kind", ["network", "api"])
def test_errors_do_not_expose_api_key(error_kind: str) -> None:
    client = create_client()
    request = httpx.Request(
        "POST",
        "https://llm.example.test/v1/responses",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    if error_kind == "network":
        error = APIConnectionError(message=API_KEY, request=request)
        expected_error = LLMConnectionError
    else:
        response = httpx.Response(500, request=request)
        error = BadRequestError(API_KEY, response=response, body={"key": API_KEY})
        expected_error = LLMProviderError
    client.responses.create.side_effect = error

    with pytest.raises(expected_error) as raised:
        OpenAILLMService(client, "synthetic-model").generate("Question synthétique")

    assert API_KEY not in str(raised.value)


def test_prompt_is_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    prompt = "Prompt privé synthétique"
    service = OpenAILLMService(create_client(), "synthetic-model")

    with caplog.at_level(logging.DEBUG):
        service.generate(prompt)

    assert prompt not in caplog.text
