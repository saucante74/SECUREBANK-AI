import builtins
import importlib
from types import ModuleType
from unittest.mock import MagicMock, call

import pytest

import app.services.langfuse_sdk_client as sdk_client_module
from app.services.langfuse_sdk_client import (
    LangfuseSdkObservationClient,
    create_langfuse_sdk_observation_client,
)
from app.services.rag_observer import RagRequestStatus


def create_client() -> tuple[
    LangfuseSdkObservationClient,
    MagicMock,
    MagicMock,
]:
    sdk = MagicMock()
    trace = MagicMock()
    sdk.start_observation.return_value = trace
    return LangfuseSdkObservationClient(sdk), sdk, trace


def test_factory_constructs_confirmed_langfuse_v4_client_explicitly() -> None:
    sdk = MagicMock()
    sdk_factory = MagicMock(return_value=sdk)
    span_filter = MagicMock()

    client = create_langfuse_sdk_observation_client(
        public_key="synthetic-public-key",
        secret_key="synthetic-secret-key",
        host="https://langfuse.example.test/",
        sdk_factory=sdk_factory,
        span_filter=span_filter,
    )

    assert isinstance(client, LangfuseSdkObservationClient)
    sdk_factory.assert_called_once_with(
        public_key="synthetic-public-key",
        secret_key="synthetic-secret-key",
        base_url="https://langfuse.example.test/",
        debug=False,
        should_export_span=span_filter,
    )


def test_sdk_module_import_does_not_import_langfuse_or_create_network_client(
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
    importlib.reload(sdk_client_module)

    assert all(not name.startswith("langfuse") for name in imported_modules)


def test_sdk_client_maps_correlated_successful_trace_without_business_data() -> None:
    client, sdk, trace = create_client()
    retrieval = MagicMock()
    generation = MagicMock()
    trace.start_observation.side_effect = [retrieval, generation]

    client.start_trace(trace_id="0123456789abcdef0123456789abcdef")
    client.record_retrieval(
        trace_id="0123456789abcdef0123456789abcdef",
        duration_seconds=0.25,
        passage_count=3,
    )
    client.record_generation(
        trace_id="0123456789abcdef0123456789abcdef",
        duration_seconds=0.5,
        model="synthetic-model",
    )
    client.finish_trace(
        trace_id="0123456789abcdef0123456789abcdef",
        status=RagRequestStatus.SUCCESS,
    )

    sdk.start_observation.assert_called_once_with(
        trace_context={"trace_id": "0123456789abcdef0123456789abcdef"},
        name="rag-request",
        as_type="span",
    )
    assert trace.start_observation.call_args_list == [
        call(
            name="rag-retrieval",
            as_type="retriever",
            metadata={"duration_seconds": 0.25, "passage_count": 3},
        ),
        call(
            name="rag-generation",
            as_type="generation",
            metadata={"duration_seconds": 0.5},
            model="synthetic-model",
        ),
    ]
    retrieval.end.assert_called_once_with()
    generation.end.assert_called_once_with()
    trace.update.assert_called_once_with(level="DEFAULT", status_message="success")
    trace.end.assert_called_once_with()

    exported_values = repr(
        [
            sdk.start_observation.call_args,
            *trace.start_observation.call_args_list,
            trace.update.call_args,
        ]
    )
    for sensitive_value in (
        "private question",
        "private prompt",
        "private answer",
        "private document",
        "private passage",
        "private source",
        "private citation",
        "synthetic.jwt.value",
        "synthetic-api-key",
        "raw exception",
    ):
        assert sensitive_value not in exported_values
    assert "input" not in exported_values
    assert "output" not in exported_values


def test_sdk_client_maps_error_status_without_exception_details() -> None:
    client, _, trace = create_client()

    client.start_trace(trace_id="trace-error")
    client.finish_trace(
        trace_id="trace-error",
        status=RagRequestStatus.ERROR,
    )

    trace.update.assert_called_once_with(level="ERROR", status_message="error")
    trace.end.assert_called_once_with()


def test_sdk_client_no_passages_trace_has_no_generation() -> None:
    client, _, trace = create_client()
    retrieval = MagicMock()
    trace.start_observation.return_value = retrieval

    client.start_trace(trace_id="trace-no-passages")
    client.record_retrieval(
        trace_id="trace-no-passages",
        duration_seconds=0.1,
        passage_count=0,
    )
    client.finish_trace(
        trace_id="trace-no-passages",
        status=RagRequestStatus.SUCCESS,
    )

    trace.start_observation.assert_called_once_with(
        name="rag-retrieval",
        as_type="retriever",
        metadata={"duration_seconds": 0.1, "passage_count": 0},
    )


def test_sdk_client_supports_successful_abstention_lifecycle() -> None:
    client, _, trace = create_client()
    trace.start_observation.side_effect = [MagicMock(), MagicMock()]

    client.start_trace(trace_id="trace-abstention")
    client.record_retrieval(
        trace_id="trace-abstention",
        duration_seconds=0.1,
        passage_count=1,
    )
    client.record_generation(
        trace_id="trace-abstention",
        duration_seconds=0.2,
        model="synthetic-model",
    )
    client.finish_trace(
        trace_id="trace-abstention",
        status=RagRequestStatus.SUCCESS,
    )

    trace.update.assert_called_once_with(level="DEFAULT", status_message="success")


def test_finished_trace_is_removed_even_when_sdk_update_fails() -> None:
    client, _, trace = create_client()
    trace.update.side_effect = RuntimeError("synthetic SDK failure")

    client.start_trace(trace_id="trace-failure")
    with pytest.raises(RuntimeError, match="synthetic SDK failure"):
        client.finish_trace(
            trace_id="trace-failure",
            status=RagRequestStatus.ERROR,
        )

    trace.end.assert_called_once_with()
    with pytest.raises(KeyError):
        client.record_retrieval(
            trace_id="trace-failure",
            duration_seconds=0.1,
            passage_count=1,
        )
