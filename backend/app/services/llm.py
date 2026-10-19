from typing import Protocol

from openai import APIConnectionError, APIError, APIStatusError, OpenAI

from app.core.config import Settings

SYSTEM_PROMPT = "Tu es un assistant qui répond en français."


class LLMService(Protocol):
    def generate(self, prompt: str) -> str: ...


class LLMResponse(Protocol):
    output_text: str


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

    def generate(self, prompt: str) -> str:
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
        return text


def create_openai_llm_service(settings: Settings) -> OpenAILLMService:
    if settings.llm_api_key is None:
        raise ValueError("LLM API key is not configured")

    client = OpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    return OpenAILLMService(client=client, model=settings.llm_model)
