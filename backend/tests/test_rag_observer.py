import builtins
import importlib
import inspect
from types import ModuleType

import pytest

import app.services.rag_observer as rag_observer_module
from app.services.rag_observer import NoOpRagObserver, RagObserver, RagRequestStatus


def use_observer(observer: RagObserver) -> None:
    observer.on_request_started()
    observer.on_retrieval_completed(duration_seconds=0.25, passage_count=3)
    observer.on_generation_completed(
        duration_seconds=0.5,
        model="synthetic-model",
        input_tokens=100,
        output_tokens=25,
        total_tokens=125,
    )
    observer.on_request_completed(
        status=RagRequestStatus.SUCCESS,
        total_duration_seconds=0.75,
        abstained=False,
    )


def test_noop_rag_observer_accepts_only_technical_measurements() -> None:
    observer = NoOpRagObserver()

    assert use_observer(observer) is None
    assert vars(observer) == {}


def test_rag_observer_contract_has_no_sensitive_content_fields() -> None:
    expected_parameters = {
        "on_request_started": {"self"},
        "on_retrieval_completed": {
            "self",
            "duration_seconds",
            "passage_count",
        },
        "on_generation_completed": {
            "self",
            "duration_seconds",
            "model",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        },
        "on_request_completed": {
            "self",
            "status",
            "total_duration_seconds",
            "abstained",
        },
    }

    for method_name, parameter_names in expected_parameters.items():
        method = getattr(RagObserver, method_name)
        assert set(inspect.signature(method).parameters) == parameter_names


def test_rag_observer_status_values_are_closed() -> None:
    assert set(RagRequestStatus) == {
        RagRequestStatus.SUCCESS,
        RagRequestStatus.ERROR,
    }


def test_observer_module_does_not_import_langfuse(
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
    importlib.reload(rag_observer_module)

    assert all(not name.startswith("langfuse") for name in imported_modules)
