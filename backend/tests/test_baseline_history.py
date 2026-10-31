import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from app.services.baseline_history import (
    BaselineRun,
    build_baseline_run,
    load_baseline_runs,
    save_baseline_run,
)


def create_comparison() -> MagicMock:
    comparison = MagicMock()
    comparison.report_at_1.mean_source_hit_at_k = 0.75
    comparison.report_at_3.mean_source_hit_at_k = 0.9
    comparison.report_at_1.mean_evidence_hit_at_k = 0.7
    comparison.report_at_3.mean_evidence_hit_at_k = 0.85
    comparison.mean_latency_seconds = 0.012
    comparison.latency_p50_seconds = 0.01
    comparison.latency_p95_seconds = 0.02
    comparison.error_rate = 0.025
    comparison.mean_returned_chunk_count = 2.8
    comparison.mean_distinct_document_count_at_3 = 2.1
    comparison.mean_source_diversity_at_3 = 0.75
    return comparison


def test_baseline_run_separates_measured_and_uncomputed_metrics() -> None:
    run = build_baseline_run(
        {"RRF": create_comparison()},
        code_version="a" * 40,
        created_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        run_id="run-1",
    )

    assert run.measured_metrics["RRF"]["source_hit_at_1"] == 0.75
    assert run.measured_metrics["RRF"]["latency_p50_seconds"] == 0.01
    assert run.measured_metrics["RRF"]["latency_p95_seconds"] == 0.02
    assert run.measured_metrics["RRF"]["error_rate"] == 0.025
    assert run.measured_metrics["RRF"]["mean_returned_chunk_count"] == 2.8
    assert run.measured_metrics["RRF"]["mean_distinct_document_count_at_3"] == 2.1
    assert run.measured_metrics["RRF"]["mean_source_diversity_at_3"] == 0.75
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


def test_historical_metric_shape_remains_loadable(tmp_path: Path) -> None:
    historical_path = (
        Path(__file__).resolve().parents[1]
        / "benchmark_results"
        / "20261030T150643Z_9f7d9cadfc6f4033b3448b5515e1ee21.json"
    )
    payload = json.loads(historical_path.read_text(encoding="utf-8"))
    path = tmp_path / historical_path.name
    path.write_text(json.dumps(payload), encoding="utf-8")

    runs = load_baseline_runs(tmp_path)

    assert len(runs) == 1
    assert isinstance(runs[0], BaselineRun)
    assert set(runs[0].measured_metrics["BM25"]) == {
        "source_hit_at_1",
        "source_hit_at_3",
        "evidence_hit_at_1",
        "evidence_hit_at_3",
        "mean_latency_seconds",
    }


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
