import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.services.baseline_history import (
    BaselineRun,
    build_baseline_run,
    load_baseline_runs,
    save_baseline_run,
)
from app.services.benchmark_dataset import create_v2_metadata
from app.services.retrieval_evaluation import AggregatedMetric


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
    comparison.ir_report_at_1 = None
    comparison.ir_report_at_3 = None
    return comparison


def create_ir_report(value: float, evaluated: int, unavailable: int) -> MagicMock:
    aggregate = AggregatedMetric(
        value=value,
        evaluated_question_count=evaluated,
        unavailable_question_count=unavailable,
    )
    report = MagicMock()
    report.precision_at_k = aggregate
    report.recall_at_k = aggregate
    report.f1_at_k = aggregate
    report.map_at_k = aggregate
    report.success_at_k = aggregate
    report.mrr_at_k = aggregate
    report.ndcg_at_k = aggregate
    return report


def create_unannotated_comparison() -> MagicMock:
    comparison = create_comparison()
    comparison.report_at_1 = None
    comparison.report_at_3 = None
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


def test_v2_run_serializes_null_relevance_metrics(tmp_path: Path) -> None:
    run = build_baseline_run(
        {"RRF": create_unannotated_comparison()},
        code_version="b" * 40,
        created_at=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        run_id="v2-run",
        metadata=create_v2_metadata(),
    )

    path = save_baseline_run(run, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload["measured_metrics"]["RRF"]

    assert payload["benchmark_id"] == "securebank-rag-retrieval-v2"
    assert payload["rag_configuration"]["corpus_version"] == "v2"
    assert payload["rag_configuration"]["chunker"] == "structured"
    assert payload["rag_configuration"]["chunk_size_characters"] == 500
    assert payload["rag_configuration"]["chunk_overlap_characters"] == 75
    assert payload["rag_configuration"]["qdrant_collection"] == (
        "securebank_benchmark_chunks_v2"
    )
    assert metrics["source_hit_at_1"] is None
    assert metrics["source_hit_at_3"] is None
    assert metrics["evidence_hit_at_1"] is None
    assert metrics["evidence_hit_at_3"] is None
    assert metrics["mean_latency_seconds"] == 0.012
    assert "ir_metrics" not in payload
    assert load_baseline_runs(tmp_path) == [run]


def test_v2_run_serializes_ir_values_and_question_counts(tmp_path: Path) -> None:
    comparison = create_comparison()
    comparison.ir_report_at_1 = create_ir_report(0.75, 36, 2)
    comparison.ir_report_at_3 = create_ir_report(0.85, 35, 3)
    run = build_baseline_run(
        {"RRF": comparison},
        code_version="b" * 40,
        created_at=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
        run_id="v2-ir-run",
        metadata=create_v2_metadata().model_copy(
            update={"relevance_annotations": True}
        ),
    )

    path = save_baseline_run(run, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    ir_metrics = payload["ir_metrics"]["RRF"]

    assert ir_metrics["judgment_source"] == "qwen"
    assert ir_metrics["precision_at_1"] == {
        "value": 0.75,
        "evaluated_question_count": 36,
        "unavailable_question_count": 2,
    }
    assert ir_metrics["precision_at_3"] == {
        "value": 0.85,
        "evaluated_question_count": 35,
        "unavailable_question_count": 3,
    }
    assert set(ir_metrics) == {
        "judgment_source",
        "precision_at_1",
        "precision_at_3",
        "recall_at_1",
        "recall_at_3",
        "f1_at_1",
        "f1_at_3",
        "map_at_3",
        "success_at_1",
        "success_at_3",
        "mrr_at_3",
        "ndcg_at_3",
    }
    assert load_baseline_runs(tmp_path) == [run]


def test_operational_metrics_cannot_be_null() -> None:
    run = build_baseline_run(
        {"RRF": create_unannotated_comparison()},
        code_version="b" * 40,
        run_id="v2-run",
        metadata=create_v2_metadata(),
    )
    payload = run.model_dump()
    payload["measured_metrics"]["RRF"]["mean_latency_seconds"] = None

    with pytest.raises(
        ValidationError,
        match="only unavailable relevance metrics may be null",
    ):
        BaselineRun.model_validate(payload)


def test_v1_relevance_metrics_cannot_be_null() -> None:
    run = build_baseline_run(
        {"RRF": create_comparison()},
        code_version="a" * 40,
        run_id="v1-run",
    )
    payload = run.model_dump()
    for name in (
        "source_hit_at_1",
        "source_hit_at_3",
        "evidence_hit_at_1",
        "evidence_hit_at_3",
    ):
        payload["measured_metrics"]["RRF"][name] = None

    with pytest.raises(
        ValidationError, match="v1 relevance metrics must remain numeric"
    ):
        BaselineRun.model_validate(payload)


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
