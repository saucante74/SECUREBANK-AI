from collections.abc import Callable
from contextvars import ContextVar
from typing import Protocol
from uuid import uuid4

from app.services.rag_observer import RagRequestStatus


class LangfuseObservationClient(Protocol):
    def start_trace(self, *, trace_id: str) -> None: ...

    def record_retrieval(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        passage_count: int,
    ) -> None: ...

    def record_generation(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        model: str,
    ) -> None: ...

    def finish_trace(
        self,
        *,
        trace_id: str,
        status: RagRequestStatus,
    ) -> None: ...


def create_trace_id() -> str:
    return uuid4().hex


class LangfuseRagObserver:
    def __init__(
        self,
        client: LangfuseObservationClient,
        trace_id_factory: Callable[[], str] = create_trace_id,
    ) -> None:
        self._client = client
        self._trace_id_factory = trace_id_factory
        self._trace_id: ContextVar[str | None] = ContextVar(
            "langfuse_rag_trace_id",
            default=None,
        )

    def on_request_started(self) -> None:
        try:
            trace_id = self._trace_id_factory()
        except Exception:
            self._trace_id.set(None)
            return None
        if not isinstance(trace_id, str) or not trace_id:
            self._trace_id.set(None)
            return None
        self._trace_id.set(trace_id)
        self._observe(lambda: self._client.start_trace(trace_id=trace_id))

    def on_retrieval_completed(
        self,
        *,
        duration_seconds: float,
        passage_count: int,
    ) -> None:
        trace_id = self._trace_id.get()
        if trace_id is None:
            return None
        self._observe(
            lambda: self._client.record_retrieval(
                trace_id=trace_id,
                duration_seconds=duration_seconds,
                passage_count=passage_count,
            )
        )

    def on_generation_completed(
        self,
        *,
        duration_seconds: float,
        model: str,
    ) -> None:
        trace_id = self._trace_id.get()
        if trace_id is None:
            return None
        self._observe(
            lambda: self._client.record_generation(
                trace_id=trace_id,
                duration_seconds=duration_seconds,
                model=model,
            )
        )

    def on_request_completed(self, *, status: RagRequestStatus) -> None:
        trace_id = self._trace_id.get()
        self._trace_id.set(None)
        if trace_id is None:
            return None
        self._observe(
            lambda: self._client.finish_trace(
                trace_id=trace_id,
                status=status,
            )
        )

    @staticmethod
    def _observe(operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception:
            return None
