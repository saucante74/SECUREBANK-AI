import argparse
from collections.abc import Callable, Sequence
from typing import Protocol

from openai import OpenAI

from app.core.config import Settings
from app.services.llm import LLMClient, LLMService, LLMServiceError, OpenAILLMService

ALLOW_REAL_CALL_FLAG = "--allow-real-openai-call"
SMOKE_PROMPT = (
    "Répondez en français par une phrase courte à cette question publique : "
    "combien font deux plus deux ?"
)
SMOKE_TIMEOUT_SECONDS = 15.0


class OpenAIClientFactory(Protocol):
    def __call__(
        self,
        *,
        api_key: str,
        base_url: str | None,
        timeout: float,
        max_retries: int,
    ) -> LLMClient: ...


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one explicitly authorized OpenAI smoke-test call."
    )
    parser.add_argument(ALLOW_REAL_CALL_FLAG, action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def create_smoke_service(
    settings: Settings,
    client_factory: OpenAIClientFactory = OpenAI,
) -> OpenAILLMService:
    if settings.llm_api_key is None:
        raise ValueError("OpenAI smoke-test configuration is unavailable")
    client = client_factory(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=SMOKE_TIMEOUT_SECONDS,
        max_retries=0,
    )
    return OpenAILLMService(client=client, model=settings.llm_model)


def main(
    argv: Sequence[str] | None = None,
    settings_factory: Callable[[], Settings] = Settings,
    service_factory: Callable[[Settings], LLMService] = create_smoke_service,
) -> int:
    arguments = parse_arguments(argv)
    if not arguments.allow_real_openai_call:
        print(
            "OpenAI smoke test disabled. "
            f"Use {ALLOW_REAL_CALL_FLAG} to authorize one real call."
        )
        return 0

    try:
        settings = settings_factory()
    except ValueError:
        print("OpenAI smoke test configuration is unavailable.")
        return 1
    if settings.llm_api_key is None:
        print("OpenAI smoke test configuration is unavailable.")
        return 1

    try:
        service = service_factory(settings)
        service.generate(SMOKE_PROMPT)
    except (LLMServiceError, OSError, ValueError):
        print("OpenAI smoke test failed.")
        return 1

    print("OpenAI smoke test succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
