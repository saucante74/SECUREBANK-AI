import builtins
import importlib
import inspect
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from types import ModuleType

import pytest

import app.services.langfuse_rag_observer as langfuse_observer_module
from app.services.langfuse_rag_observer import (
    LangfuseObservationClient,
    LangfuseRagObserver,
)
from app.services.rag_observer import RagObserver, RagRequestStatus


class MemoryObservationClient:
    def __init__(self, failing_operations: set[str] | None = None) -> None:
        self.events: list[tuple[object, ...]] = []
        self._failing_operations = failing_operations or set()
        self._lock = Lock()

    def _record(self, operation: str, *values: object) -> None:
        with self._lock:
            self.events.append((operation, *values))
        if operation in self._failing_operations:
            raise RuntimeError("synthetic observability failure")

    def start_trace(self, *, trace_id: str) -> None:
        self._record("start", trace_id)

    def record_retrieval(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        passage_count: int,
    ) -> None:
        self._record("retrieval", trace_id, duration_seconds, passage_count)

    def record_generation(
        self,
        *,
        trace_id: str,
        duration_seconds: float,
        model: str,
    ) -> None:
        self._record("generation", trace_id, duration_seconds, model)

    def finish_trace(
        self,
        *,
        trace_id: str,
        status: RagRequestStatus,
    ) -> None:
        self._record("finish", trace_id, status)


def create_observer(
    client: MemoryObservationClient,
    trace_ids: list[str],
) -> LangfuseRagObserver:
    trace_id_iterator = iter(trace_ids)
    return LangfuseRagObserver(client, trace_id_factory=trace_id_iterator.__next__)


def accept_rag_observer(observer: RagObserver) -> RagObserver:
    return observer


def test_adapter_conforms_to_rag_observer_and_uses_injected_client() -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, ["trace-1"])

    assert accept_rag_observer(observer) is observer
    assert observer._client is client


def test_successful_generation_records_one_ordered_trace() -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, ["trace-1"])

    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.25, passage_count=2)
    observer.on_generation_completed(
        duration_seconds=0.5,
        model="synthetic-model",
    )
    observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    assert client.events == [
        ("start", "trace-1"),
        ("retrieval", "trace-1", 0.25, 2),
        ("generation", "trace-1", 0.5, "synthetic-model"),
        ("finish", "trace-1", RagRequestStatus.SUCCESS),
    ]


def test_abstention_uses_the_same_successful_trace_lifecycle() -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, ["trace-abstention"])

    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.1, passage_count=1)
    observer.on_generation_completed(
        duration_seconds=0.2,
        model="synthetic-model",
    )
    observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    assert {event[1] for event in client.events} == {"trace-abstention"}
    assert client.events[-1] == (
        "finish",
        "trace-abstention",
        RagRequestStatus.SUCCESS,
    )


def test_no_passages_finishes_without_generation_event() -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, ["trace-no-passages"])

    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.1, passage_count=0)
    observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    assert client.events == [
        ("start", "trace-no-passages"),
        ("retrieval", "trace-no-passages", 0.1, 0),
        ("finish", "trace-no-passages", RagRequestStatus.SUCCESS),
    ]


@pytest.mark.parametrize("failed_stage", ["retrieval", "generation", "validation"])
def test_pipeline_failures_finish_the_trace_with_error(failed_stage: str) -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, [f"trace-{failed_stage}"])

    observer.on_request_started()
    if failed_stage != "retrieval":
        observer.on_retrieval_completed(duration_seconds=0.1, passage_count=1)
    if failed_stage == "validation":
        observer.on_generation_completed(
            duration_seconds=0.2,
            model="synthetic-model",
        )
    observer.on_request_completed(status=RagRequestStatus.ERROR)

    assert client.events[-1] == (
        "finish",
        f"trace-{failed_stage}",
        RagRequestStatus.ERROR,
    )


def test_client_failures_are_isolated_for_every_operation() -> None:
    client = MemoryObservationClient({"start", "retrieval", "generation", "finish"})
    observer = create_observer(client, ["trace-1"])

    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.1, passage_count=1)
    observer.on_generation_completed(
        duration_seconds=0.2,
        model="synthetic-model",
    )
    observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    assert [event[0] for event in client.events] == [
        "start",
        "retrieval",
        "generation",
        "finish",
    ]


def test_internal_client_contract_excludes_sensitive_and_arbitrary_fields() -> None:
    expected_parameters = {
        "start_trace": {"self", "trace_id"},
        "record_retrieval": {
            "self",
            "trace_id",
            "duration_seconds",
            "passage_count",
        },
        "record_generation": {
            "self",
            "trace_id",
            "duration_seconds",
            "model",
        },
        "finish_trace": {"self", "trace_id", "status"},
    }

    for method_name, parameter_names in expected_parameters.items():
        method = getattr(LangfuseObservationClient, method_name)
        assert set(inspect.signature(method).parameters) == parameter_names


def test_observation_events_exclude_sensitive_pipeline_data() -> None:
    client = MemoryObservationClient()
    observer = create_observer(client, ["trace-1"])
    sensitive_values = (
        "private question",
        "private prompt",
        "private answer",
        "private passage",
        "synthetic.jwt.value",
        "synthetic-api-key",
    )

    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.1, passage_count=1)
    observer.on_generation_completed(
        duration_seconds=0.2,
        model="synthetic-model",
    )
    observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    recorded_events = repr(client.events)
    for sensitive_value in sensitive_values:
        assert sensitive_value not in recorded_events


def test_concurrent_requests_keep_independent_trace_contexts() -> None:
    client = MemoryObservationClient()
    observer = LangfuseRagObserver(client)
    barrier = Barrier(2)

    def record_request(passage_count: int) -> None:
        observer.on_request_started()
        barrier.wait()
        observer.on_retrieval_completed(
            duration_seconds=0.1,
            passage_count=passage_count,
        )
        observer.on_generation_completed(
            duration_seconds=0.2,
            model="synthetic-model",
        )
        observer.on_request_completed(status=RagRequestStatus.SUCCESS)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(record_request, count) for count in (1, 2)]
        for future in futures:
            future.result()

    events_by_trace: dict[str, list[tuple[object, ...]]] = defaultdict(list)
    for event in client.events:
        events_by_trace[str(event[1])].append(event)

    assert len(events_by_trace) == 2
    assert {events[1][3] for events in events_by_trace.values()} == {1, 2}
    for trace_id, events in events_by_trace.items():
        assert [event[0] for event in events] == [
            "start",
            "retrieval",
            "generation",
            "finish",
        ]
        assert {event[1] for event in events} == {trace_id}


def test_adapter_module_does_not_import_langfuse_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_modules: list[str] = []
    original_import = builtins.__import__

    def tracked_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        imported_modules.append(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", tracked_import)
    importlib.reload(langfuse_observer_module)

    assert all(not name.startswith("langfuse") for name in imported_modules)
