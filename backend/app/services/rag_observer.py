from enum import StrEnum
from typing import Protocol


class RagRequestStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class RagObserver(Protocol):
    def on_request_started(self) -> None: ...

    def on_retrieval_completed(
        self,
        *,
        duration_seconds: float,
        passage_count: int,
    ) -> None: ...

    def on_generation_completed(
        self,
        *,
        duration_seconds: float,
        model: str,
    ) -> None: ...

    def on_request_completed(self, *, status: RagRequestStatus) -> None: ...


class NoOpRagObserver:
    def on_request_started(self) -> None:
        return None

    def on_retrieval_completed(
        self,
        *,
        duration_seconds: float,
        passage_count: int,
    ) -> None:
        return None

    def on_generation_completed(
        self,
        *,
        duration_seconds: float,
        model: str,
    ) -> None:
        return None

    def on_request_completed(self, *, status: RagRequestStatus) -> None:
        return None
