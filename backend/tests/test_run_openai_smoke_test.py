from typing import Any
from unittest.mock import Mock

from pydantic import SecretStr

from app.core.config import Settings
from app.services.llm import LLMProviderError, OpenAILLMService
from scripts.run_openai_smoke_test import (
    ALLOW_REAL_CALL_FLAG,
    SMOKE_PROMPT,
    SMOKE_TIMEOUT_SECONDS,
    create_smoke_service,
    main,
)


class FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponsesClient:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, str]] = []

    def create(self, *, model: str, instructions: str, input: str) -> FakeResponse:
        self.calls.append(
            {"model": model, "instructions": instructions, "input": input}
        )
        return FakeResponse(self.output_text)


class FakeClient:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponsesClient(output_text)


class FakeSmokeService:
    def __init__(
        self,
        output: str = "synthetic response",
        error: Exception | None = None,
    ) -> None:
        self.output = output
        self.error = error
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.output


class RecordingClientFactory:
    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> FakeClient:
        self.calls.append(kwargs)
        return self.client


def make_settings(api_key: str | None = "synthetic-smoke-key") -> Settings:
    return Settings(
        _env_file=None,
        llm_api_key=SecretStr(api_key) if api_key is not None else None,
        llm_model="synthetic-model",
        llm_base_url="https://synthetic.invalid/v1",
    )


def test_default_mode_constructs_nothing_and_makes_no_call(capsys: Any) -> None:
    settings_factory = Mock(side_effect=AssertionError("settings must not load"))
    service_factory = Mock(side_effect=AssertionError("client must not exist"))

    exit_code = main(
        [],
        settings_factory=settings_factory,
        service_factory=service_factory,
    )

    assert exit_code == 0
    settings_factory.assert_not_called()
    service_factory.assert_not_called()
    assert "disabled" in capsys.readouterr().out


def test_authorized_mode_rejects_missing_api_key(capsys: Any) -> None:
    service_factory = Mock(side_effect=AssertionError("client must not exist"))

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=lambda: make_settings(None),
        service_factory=service_factory,
    )

    assert exit_code == 1
    service_factory.assert_not_called()
    assert capsys.readouterr().out == (
        "OpenAI smoke test configuration is unavailable.\n"
    )


def test_invalid_configuration_does_not_expose_sensitive_message(
    capsys: Any,
) -> None:
    sensitive_message = "invalid setting containing synthetic-smoke-key"
    service_factory = Mock(side_effect=AssertionError("client must not exist"))

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=Mock(side_effect=ValueError(sensitive_message)),
        service_factory=service_factory,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    service_factory.assert_not_called()
    assert output == "OpenAI smoke test configuration is unavailable.\n"
    assert sensitive_message not in output
    assert "synthetic-smoke-key" not in output


def test_authorized_mode_makes_one_call_without_printing_response(
    capsys: Any,
) -> None:
    service = FakeSmokeService(output="private raw response")
    service_factory = Mock(return_value=service)

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=make_settings,
        service_factory=service_factory,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    service_factory.assert_called_once()
    assert service.prompts == [SMOKE_PROMPT]
    assert output == "OpenAI smoke test succeeded.\n"
    assert "private raw response" not in output
    assert "synthetic-smoke-key" not in output


def test_smoke_service_disables_retries_and_uses_fixed_timeout() -> None:
    client = FakeClient("synthetic response")
    client_factory = RecordingClientFactory(client)

    service = create_smoke_service(make_settings(), client_factory)
    result = service.generate(SMOKE_PROMPT)

    assert result == "synthetic response"
    assert client_factory.calls == [
        {
            "api_key": "synthetic-smoke-key",
            "base_url": "https://synthetic.invalid/v1",
            "timeout": SMOKE_TIMEOUT_SECONDS,
            "max_retries": 0,
        }
    ]
    assert len(client.responses.calls) == 1
    assert client.responses.calls[0]["model"] == "synthetic-model"
    assert client.responses.calls[0]["input"] == SMOKE_PROMPT


def test_empty_response_produces_only_generic_error(capsys: Any) -> None:
    client = FakeClient("")
    service = OpenAILLMService(client=client, model="synthetic-model")

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=make_settings,
        service_factory=lambda settings: service,
    )

    assert exit_code == 1
    assert len(client.responses.calls) == 1
    assert capsys.readouterr().out == "OpenAI smoke test failed.\n"


def test_provider_error_does_not_expose_sensitive_message(capsys: Any) -> None:
    sensitive_message = "provider error containing synthetic-smoke-key"
    service = FakeSmokeService(error=LLMProviderError(sensitive_message))

    exit_code = main(
        [ALLOW_REAL_CALL_FLAG],
        settings_factory=make_settings,
        service_factory=lambda settings: service,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert service.prompts == [SMOKE_PROMPT]
    assert output == "OpenAI smoke test failed.\n"
    assert sensitive_message not in output
    assert "synthetic-smoke-key" not in output
