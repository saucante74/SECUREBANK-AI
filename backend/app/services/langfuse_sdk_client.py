from collections.abc import Callable
from threading import Lock
from typing import Protocol

from app.services.rag_observer import RagRequestStatus


class LangfuseSdkObservation(Protocol):
    def start_observation(
        self,
        *,
        name: str,
        as_type: str,
        metadata: dict[str, float | int] | None = None,
        model: str | None = None,
    ) -> "LangfuseSdkObservation": ...

    def update(
        self,
        *,
        level: str,
        status_message: str,
    ) -> "LangfuseSdkObservation": ...

    def end(self) -> "LangfuseSdkObservation": ...


class LangfuseSdk(Protocol):
    def start_observation(
        self,
        *,
        trace_context: dict[str, str],
        name: str,
        as_type: str,
    ) -> LangfuseSdkObservation: ...


class LangfuseSdkObservationClient:
    def __init__(self, sdk: LangfuseSdk) -> None:
        self._sdk = sdk
        self._traces: dict[str, LangfuseSdkObservation] = {}
        self._lock = Lock()

    def start_trace(self, *, trace_id: str) -> None:
        trace = self._sdk.start_observation(
            trace_context={"trace_id": trace_id},
            name="rag-request",
            as_type="span",
        )
        with self._lock:
            self._traces[trace_id] = trace

    def record_retrieval(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        passage_count: int,
    ) -> None:
        trace = self._get_trace(trace_id)
        observation = trace.start_observation(
            name="rag-retrieval",
            as_type="retriever",
            metadata={
                "duration_seconds": duration_seconds,
                "passage_count": passage_count,
            },
        )
        observation.end()

    def record_generation(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        model: str,
    ) -> None:
        trace = self._get_trace(trace_id)
        observation = trace.start_observation(
            name="rag-generation",
            as_type="generation",
            metadata={"duration_seconds": duration_seconds},
            model=model,
        )
        observation.end()

    def finish_trace(
        self,
        *,
        trace_id: str,
        status: RagRequestStatus,
    ) -> None:
        with self._lock:
            trace = self._traces.pop(trace_id)
        level = "ERROR" if status is RagRequestStatus.ERROR else "DEFAULT"
        try:
            trace.update(level=level, status_message=status.value)
        finally:
            trace.end()

    def _get_trace(self, trace_id: str) -> LangfuseSdkObservation:
        with self._lock:
            return self._traces[trace_id]


def create_langfuse_sdk_observation_client(
    *,
    public_key: str,
    secret_key: str,
    host: str,
    sdk_factory: Callable[..., LangfuseSdk] | None = None,
    span_filter: Callable[[object], bool] | None = None,
) -> LangfuseSdkObservationClient:
    if sdk_factory is None:
        from langfuse import Langfuse, is_langfuse_span

        sdk_factory = Langfuse
        span_filter = is_langfuse_span
    if span_filter is None:
        raise ValueError("A Langfuse SDK span filter is required")
    sdk = sdk_factory(
        public_key=public_key,
        secret_key=secret_key,
        base_url=host,
        debug=False,
        should_export_span=span_filter,
    )
    return LangfuseSdkObservationClient(sdk)
