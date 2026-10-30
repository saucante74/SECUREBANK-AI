import json
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.services.benchmark_dataset import (
    BENCHMARK_CHUNK_OVERLAP,
    BENCHMARK_CHUNK_SIZE,
    BENCHMARK_COLLECTION_NAME,
)
from app.services.embeddings import DEFAULT_MODEL_NAME
from app.services.reranking import DEFAULT_RERANKER_MODEL
from scripts.compare_retrievers import EngineComparison

BENCHMARK_RESULTS_DIR = Path(__file__).resolve().parents[2] / "benchmark_results"


class ParameterChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    previous_value: str | int | float | bool | None
    new_value: str | int | float | bool | None


class BaselineRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_id: str
    run_id: str
    created_at: datetime
    code_version: str
    rag_configuration: dict[str, Any]
    parameter_change: ParameterChange | None
    measured_metrics: dict[str, dict[str, float]]
    expected_behaviors: tuple[str, ...]
    uncomputed_metrics: tuple[str, ...]
    langfuse_trace_ids: tuple[str, ...]


def current_code_version(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_baseline_run(
    comparisons: Mapping[str, EngineComparison],
    code_version: str,
    created_at: datetime | None = None,
    run_id: str | None = None,
) -> BaselineRun:
    measured_metrics = {
        name: {
            "source_hit_at_1": comparison.report_at_1.mean_source_hit_at_k,
            "source_hit_at_3": comparison.report_at_3.mean_source_hit_at_k,
            "evidence_hit_at_1": comparison.report_at_1.mean_evidence_hit_at_k,
            "evidence_hit_at_3": comparison.report_at_3.mean_evidence_hit_at_k,
            "mean_latency_seconds": comparison.mean_latency_seconds,
        }
        for name, comparison in comparisons.items()
    }
    return BaselineRun(
        benchmark_id="securebank-rag-retrieval-v1",
        run_id=run_id or uuid4().hex,
        created_at=created_at or datetime.now(UTC),
        code_version=code_version,
        rag_configuration={
            "top_k": 3,
            "chunk_size_characters": BENCHMARK_CHUNK_SIZE,
            "chunk_overlap_characters": BENCHMARK_CHUNK_OVERLAP,
            "embedding_model": DEFAULT_MODEL_NAME,
            "embedding_dimension": 384,
            "qdrant_collection": BENCHMARK_COLLECTION_NAME,
            "qdrant_distance": "cosine",
            "candidate_multiplier": 3,
            "rrf_k": 60,
            "reranker_model": DEFAULT_RERANKER_MODEL,
        },
        parameter_change=None,
        measured_metrics=measured_metrics,
        expected_behaviors=(
            "answerable cases retrieve their documented source and evidence",
            "unanswerable cases abstain without citations",
            "ambiguous cases avoid unsupported assumptions",
            "grounded answers cite only retrieved passages",
            "sensitive input and output remain masked",
        ),
        uncomputed_metrics=(
            "answer_correctness",
            "abstention_accuracy",
            "citation_correctness",
            "pii_masking_recall",
        ),
        langfuse_trace_ids=(),
    )


def save_baseline_run(
    run: BaselineRun,
    results_dir: Path = BENCHMARK_RESULTS_DIR,
) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{run.created_at:%Y%m%dT%H%M%SZ}_{run.run_id}.json"
    path.write_text(
        json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
