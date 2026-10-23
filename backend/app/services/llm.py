from dataclasses import dataclass
from typing import Protocol

from openai import APIConnectionError, APIError, APIStatusError, OpenAI

from app.core.config import Settings

SYSTEM_PROMPT = "Tu es un assistant qui répond en français."


class LLMService(Protocol):
    def generate(self, prompt: str) -> "LLMGeneration": ...


@dataclass(frozen=True)
class LLMTokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMGeneration:
    text: str
    usage: LLMTokenUsage | None = None


class LLMUsage(Protocol):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMResponse(Protocol):
    output_text: str
    usage: LLMUsage | None


class ResponsesClient(Protocol):
    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
    ) -> LLMResponse: ...


class LLMClient(Protocol):
    responses: ResponsesClient


class LLMServiceError(RuntimeError):
    pass


class LLMConnectionError(LLMServiceError):
    pass


class LLMProviderError(LLMServiceError):
    pass


class LLMEmptyResponseError(LLMServiceError):
    pass


class OpenAILLMService:
    def __init__(self, client: LLMClient, model: str) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must contain non-whitespace characters")
        self._client = client
        self._model = model

    def generate(self, prompt: str) -> LLMGeneration:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must contain non-whitespace characters")

        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
            )
        except APIConnectionError:
            raise LLMConnectionError("Unable to reach the LLM provider") from None
        except (APIStatusError, APIError):
            raise LLMProviderError("The LLM provider rejected the request") from None

        text = response.output_text
        if not isinstance(text, str) or not text.strip():
            raise LLMEmptyResponseError("The LLM provider returned an empty response")
        return LLMGeneration(
            text=text,
            usage=self._extract_usage(getattr(response, "usage", None)),
        )

    @staticmethod
    def _extract_usage(usage: LLMUsage | None) -> LLMTokenUsage | None:
        if usage is None:
            return None
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        values = (input_tokens, output_tokens, total_tokens)
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in values
        ):
            return None
        if input_tokens + output_tokens != total_tokens:
            return None
        return LLMTokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


def create_openai_llm_service(settings: Settings) -> OpenAILLMService:
    if settings.llm_api_key is None:
        raise ValueError("LLM API key is not configured")

    client = OpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    return OpenAILLMService(client=client, model=settings.llm_model)
