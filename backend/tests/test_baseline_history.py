import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from app.services.baseline_history import build_baseline_run, save_baseline_run


def create_comparison() -> MagicMock:
    comparison = MagicMock()
    comparison.report_at_1.mean_source_hit_at_k = 0.75
    comparison.report_at_3.mean_source_hit_at_k = 0.9
    comparison.report_at_1.mean_evidence_hit_at_k = 0.7
    comparison.report_at_3.mean_evidence_hit_at_k = 0.85
    comparison.mean_latency_seconds = 0.012
    return comparison


def test_baseline_run_separates_measured_and_uncomputed_metrics() -> None:
    run = build_baseline_run(
        {"RRF": create_comparison()},
        code_version="a" * 40,
        created_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        run_id="run-1",
    )

    assert run.measured_metrics["RRF"]["source_hit_at_1"] == 0.75
    assert "abstention_accuracy" in run.uncomputed_metrics
    assert run.langfuse_trace_ids == ()
    assert run.parameter_change is None


def test_baseline_run_is_saved_without_overwriting_history(tmp_path: Path) -> None:
    created_at = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    first = build_baseline_run(
        {"RRF": create_comparison()},
        code_version="a" * 40,
        created_at=created_at,
        run_id="first",
    )
    second = first.model_copy(update={"run_id": "second"})

    first_path = save_baseline_run(first, tmp_path)
    second_path = save_baseline_run(second, tmp_path)

    assert first_path != second_path
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert json.loads(first_path.read_text(encoding="utf-8"))["run_id"] == "first"


def test_generation_benchmark_documents_required_case_categories() -> None:
    path = (
        Path(__file__).resolve().parents[1] / "data" / "rag_generation_benchmark.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "expectations_only"
    assert {case["category"] for case in payload["cases"]} == {
        "answerable",
        "unanswerable",
        "ambiguous",
        "citation",
        "confidentiality",
    }


def test_baseline_script_disables_onnx_telemetry_before_imports(
    tmp_path: Path,
) -> None:
    backend_path = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.pop("ORT_DISABLE_TELEMETRY", None)
    environment["PYTHONPATH"] = str(backend_path)

    result = subprocess.run(
        [sys.executable, "-c", "import scripts.run_rag_baseline"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert not (tmp_path / ":memory:.ses").exists()
