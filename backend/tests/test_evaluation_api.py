import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_settings
from app.core.config import Settings
from app.core.rbac import Role
from app.main import app
from app.services.baseline_history import BaselineRun, EngineIRMetrics

JWT_SECRET = "synthetic-evaluation-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-evaluation-test"
JWT_AUDIENCE = "securebank-ai-evaluation-api"


def create_run(
    run_id: str,
    evidence_hit: float | None = 0.7,
    include_operational_metrics: bool = False,
) -> BaselineRun:
    source_hit_at_1 = None if evidence_hit is None else 0.6
    source_hit_at_3 = None if evidence_hit is None else 0.8
    evidence_hit_at_1 = None if evidence_hit is None else 0.5
    metrics = {
        "source_hit_at_1": source_hit_at_1,
        "source_hit_at_3": source_hit_at_3,
        "evidence_hit_at_1": evidence_hit_at_1,
        "evidence_hit_at_3": evidence_hit,
        "mean_latency_seconds": 0.02,
    }
    if include_operational_metrics:
        metrics.update(
            {
                "latency_p50_seconds": 0.015,
                "latency_p95_seconds": 0.04,
                "error_rate": 0.025,
                "mean_returned_chunk_count": 2.8,
                "mean_distinct_document_count_at_3": 2.1,
                "mean_source_diversity_at_3": 0.75,
            }
        )
    return BaselineRun(
        benchmark_id=(
            "securebank-rag-retrieval-v2"
            if evidence_hit is None
            else "securebank-rag-retrieval-v1"
        ),
        run_id=run_id,
        created_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        code_version="a" * 40,
        rag_configuration={"top_k": 3, "strategy": "rrf"},
        parameter_change=None,
        measured_metrics={"RRF": metrics},
        expected_behaviors=(),
        uncomputed_metrics=("answer_correctness",),
        langfuse_trace_ids=(),
    )


def write_run(path: Path, run: BaselineRun) -> None:
    path.write_text(run.model_dump_json(), encoding="utf-8")


def create_ir_metrics() -> EngineIRMetrics:
    metric = {
        "value": 0.75,
        "evaluated_question_count": 36,
        "unavailable_question_count": 2,
    }
    unavailable_metric = {
        "value": None,
        "evaluated_question_count": 0,
        "unavailable_question_count": 38,
    }
    return EngineIRMetrics.model_validate(
        {
            "judgment_source": "qwen",
            "precision_at_1": metric,
            "precision_at_3": metric,
            "recall_at_1": metric,
            "recall_at_3": metric,
            "f1_at_1": metric,
            "f1_at_3": metric,
            "map_at_3": metric,
            "success_at_1": metric,
            "success_at_3": metric,
            "mrr_at_3": metric,
            "ndcg_at_3": unavailable_metric,
        }
    )


def create_token(role: Role) -> str:
    return jwt.encode(
        {
            "sub": "synthetic-evaluation-user",
            "role": role,
            "exp": datetime(2100, 1, 1, tzinfo=UTC),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def request(
    path: str,
    results_path: Path,
    role: Role | None = None,
    method: str = "GET",
) -> object:
    settings = Settings(
        _env_file=None,
        jwt_secret_key=JWT_SECRET,
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
        benchmark_results_path=results_path,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    headers = (
        None if role is None else {"Authorization": f"Bearer {create_token(role)}"}
    )

    async def send_request() -> object:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers)

    try:
        return asyncio.run(send_request())
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_public_user_can_list_and_read_runs(tmp_path: Path) -> None:
    write_run(tmp_path / "run.json", create_run("run-1"))

    listing = request("/evaluation/runs", tmp_path)
    detail = request("/evaluation/runs/run-1", tmp_path)

    assert listing.status_code == 200
    assert [run["run_id"] for run in listing.json()] == ["run-1"]
    assert detail.status_code == 200
    assert detail.json()["measured_metrics"]["RRF"]["evidence_hit_at_3"] == 0.7


def test_current_run_exposes_only_aggregate_operational_metrics(
    tmp_path: Path,
) -> None:
    write_run(
        tmp_path / "run.json",
        create_run("run-1", include_operational_metrics=True),
    )

    response = request("/evaluation/runs/run-1", tmp_path)

    assert response.status_code == 200
    metrics = response.json()["measured_metrics"]["RRF"]
    assert metrics == {
        "source_hit_at_1": 0.6,
        "source_hit_at_3": 0.8,
        "evidence_hit_at_1": 0.5,
        "evidence_hit_at_3": 0.7,
        "mean_latency_seconds": 0.02,
        "latency_p50_seconds": 0.015,
        "latency_p95_seconds": 0.04,
        "error_rate": 0.025,
        "mean_returned_chunk_count": 2.8,
        "mean_distinct_document_count_at_3": 2.1,
        "mean_source_diversity_at_3": 0.75,
    }
    assert "questions" not in response.text
    assert "results_by_case_id" not in response.text


def test_historical_run_exposes_missing_operational_metrics_as_null(
    tmp_path: Path,
) -> None:
    write_run(tmp_path / "run.json", create_run("historical"))

    response = request("/evaluation/runs/historical", tmp_path)

    assert response.status_code == 200
    metrics = response.json()["measured_metrics"]["RRF"]
    assert metrics["latency_p50_seconds"] is None
    assert metrics["latency_p95_seconds"] is None
    assert metrics["error_rate"] is None
    assert metrics["mean_returned_chunk_count"] is None
    assert metrics["mean_distinct_document_count_at_3"] is None
    assert metrics["mean_source_diversity_at_3"] is None


def test_v2_run_exposes_null_relevance_and_numeric_operations(
    tmp_path: Path,
) -> None:
    run = create_run(
        "v2-run",
        evidence_hit=None,
        include_operational_metrics=True,
    ).model_copy(
        update={
            "rag_configuration": {
                "top_k": 3,
                "corpus_version": "v2",
                "chunker": "structured",
            }
        }
    )
    write_run(tmp_path / "v2.json", run)

    listing = request("/evaluation/runs", tmp_path)
    detail = request("/evaluation/runs/v2-run", tmp_path)

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()[0]["rag_configuration"] == {
        "top_k": 3,
        "corpus_version": "v2",
        "chunker": "structured",
    }
    assert detail.json()["rag_configuration"] == {
        "top_k": 3,
        "corpus_version": "v2",
        "chunker": "structured",
    }
    metrics = detail.json()["measured_metrics"]["RRF"]
    assert metrics["source_hit_at_1"] is None
    assert metrics["source_hit_at_3"] is None
    assert metrics["evidence_hit_at_1"] is None
    assert metrics["evidence_hit_at_3"] is None
    assert metrics["mean_latency_seconds"] == 0.02
    assert metrics["error_rate"] == 0.025


def test_v2_run_exposes_ir_metrics_with_availability_and_source(
    tmp_path: Path,
) -> None:
    run = create_run(
        "v2-ir-run",
        include_operational_metrics=True,
    ).model_copy(update={"ir_metrics": {"RRF": create_ir_metrics()}})
    write_run(tmp_path / "v2-ir.json", run)

    response = request("/evaluation/runs/v2-ir-run", tmp_path)

    assert response.status_code == 200
    ir_metrics = response.json()["ir_metrics"]["RRF"]
    assert ir_metrics["judgment_source"] == "qwen"
    assert ir_metrics["precision_at_1"] == {
        "value": 0.75,
        "evaluated_question_count": 36,
        "unavailable_question_count": 2,
    }
    assert ir_metrics["ndcg_at_3"] == {
        "value": None,
        "evaluated_question_count": 0,
        "unavailable_question_count": 38,
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


def test_historical_run_without_ir_metrics_exposes_empty_mapping(
    tmp_path: Path,
) -> None:
    write_run(tmp_path / "historical.json", create_run("historical"))

    response = request("/evaluation/runs/historical", tmp_path)

    assert response.status_code == 200
    assert response.json()["ir_metrics"] == {}


@pytest.mark.parametrize("role", [Role.ANALYST, Role.COMPLIANCE_OFFICER, Role.ADMIN])
def test_authenticated_roles_have_the_same_read_access(
    tmp_path: Path,
    role: Role,
) -> None:
    write_run(tmp_path / "run.json", create_run("run-1"))
    response = request("/evaluation/runs", tmp_path, role)

    assert response.status_code == 200


def test_anonymous_user_has_read_access(tmp_path: Path) -> None:
    write_run(tmp_path / "run.json", create_run("run-1"))
    response = request("/evaluation/runs", tmp_path, None)

    assert response.status_code == 200


def test_missing_history_returns_an_empty_list(tmp_path: Path) -> None:
    response = request("/evaluation/runs", tmp_path / "missing")

    assert response.status_code == 200
    assert response.json() == []


def test_invalid_history_is_not_exposed(tmp_path: Path) -> None:
    (tmp_path / "invalid.json").write_text(
        json.dumps({"run_id": "invalid", "secret": "must-not-leak"}),
        encoding="utf-8",
    )

    response = request("/evaluation/runs", tmp_path)

    assert response.status_code == 503
    assert response.json() == {"detail": "Benchmark history is unavailable"}
    assert "must-not-leak" not in response.text


def test_unknown_run_returns_not_found(tmp_path: Path) -> None:
    response = request("/evaluation/runs/unknown", tmp_path)

    assert response.status_code == 404


def test_public_user_can_compare_configurations_and_each_engine(
    tmp_path: Path,
) -> None:
    previous = create_run("previous")
    new = create_run("new", evidence_hit=0.8).model_copy(
        update={"rag_configuration": {"top_k": 5, "strategy": "rrf"}}
    )
    write_run(tmp_path / "previous.json", previous)
    write_run(tmp_path / "new.json", new)

    response = request(
        "/evaluation/compare?previous_run_id=previous&new_run_id=new",
        tmp_path,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configuration_changes"] == [
        {"name": "top_k", "previous_value": 3, "new_value": 5}
    ]
    evidence_delta = next(
        item
        for item in body["metric_deltas"]
        if item["engine"] == "RRF" and item["metric"] == "evidence_hit_at_3"
    )
    assert evidence_delta["delta"] == pytest.approx(0.1)


def test_comparison_preserves_missing_historical_operational_value(
    tmp_path: Path,
) -> None:
    write_run(tmp_path / "historical.json", create_run("historical"))
    write_run(
        tmp_path / "current.json",
        create_run("current", include_operational_metrics=True),
    )

    response = request(
        "/evaluation/compare?previous_run_id=historical&new_run_id=current",
        tmp_path,
    )

    assert response.status_code == 200
    p50_delta = next(
        item
        for item in response.json()["metric_deltas"]
        if item["engine"] == "RRF" and item["metric"] == "latency_p50_seconds"
    )
    assert p50_delta == {
        "engine": "RRF",
        "metric": "latency_p50_seconds",
        "previous_value": None,
        "new_value": 0.015,
        "delta": None,
    }


def test_comparison_preserves_unavailable_v2_relevance(tmp_path: Path) -> None:
    previous = create_run("v1").model_copy(
        update={
            "rag_configuration": {
                "corpus_version": "v1",
                "chunker": "character",
            }
        }
    )
    current = create_run("v2", evidence_hit=None).model_copy(
        update={
            "rag_configuration": {
                "corpus_version": "v2",
                "chunker": "structured",
            }
        }
    )
    write_run(tmp_path / "v1.json", previous)
    write_run(tmp_path / "v2.json", current)

    response = request(
        "/evaluation/compare?previous_run_id=v1&new_run_id=v2",
        tmp_path,
    )

    assert response.status_code == 200
    assert response.json()["configuration_changes"] == [
        {
            "name": "chunker",
            "previous_value": "character",
            "new_value": "structured",
        },
        {
            "name": "corpus_version",
            "previous_value": "v1",
            "new_value": "v2",
        },
    ]
    evidence_delta = next(
        item
        for item in response.json()["metric_deltas"]
        if item["engine"] == "RRF" and item["metric"] == "evidence_hit_at_3"
    )
    assert evidence_delta == {
        "engine": "RRF",
        "metric": "evidence_hit_at_3",
        "previous_value": 0.7,
        "new_value": None,
        "delta": None,
    }


def test_public_response_excludes_internal_and_sensitive_fields(
    tmp_path: Path,
) -> None:
    run = create_run("run-1").model_copy(
        update={
            "rag_configuration": {
                "top_k": 3,
                "qdrant_collection": "internal-collection",
                "local_path": "/private/corpus.json",
                "api_secret": "must-not-leak",
                "embedding_model": "/private/model/path",
            },
            "langfuse_trace_ids": ("private-trace-id",),
            "expected_behaviors": ("private user question",),
        }
    )
    write_run(tmp_path / "run.json", run)

    response = request("/evaluation/runs", tmp_path)

    assert response.status_code == 200
    body = response.json()[0]
    assert set(body) == {
        "run_id",
        "created_at",
        "rag_configuration",
        "parameter_change",
        "measured_metrics",
        "ir_metrics",
    }
    assert body["rag_configuration"] == {"top_k": 3}
    serialized = response.text
    assert "private-trace-id" not in serialized
    assert "private user question" not in serialized
    assert "must-not-leak" not in serialized
    assert "/private/corpus.json" not in serialized
    assert "internal-collection" not in serialized
    assert "/private/model/path" not in serialized
    assert "code_version" not in serialized

    detail = request("/evaluation/runs/run-1", tmp_path)
    assert detail.status_code == 200
    assert detail.json() == body


def test_public_response_filters_unknown_benchmark_metadata_values(
    tmp_path: Path,
) -> None:
    run = create_run("run-1").model_copy(
        update={
            "rag_configuration": {
                "corpus_version": "v3",
                "chunker": "semantic",
                "top_k": 3,
            }
        }
    )
    write_run(tmp_path / "run.json", run)

    response = request("/evaluation/runs/run-1", tmp_path)

    assert response.status_code == 200
    assert response.json()["rag_configuration"] == {"top_k": 3}


def test_public_comparison_excludes_non_allowlisted_configuration(
    tmp_path: Path,
) -> None:
    previous = create_run("previous").model_copy(
        update={
            "rag_configuration": {
                "top_k": 3,
                "api_secret": "previous-secret",
            }
        }
    )
    new = create_run("new").model_copy(
        update={
            "rag_configuration": {
                "top_k": 5,
                "api_secret": "new-secret",
            }
        }
    )
    write_run(tmp_path / "previous.json", previous)
    write_run(tmp_path / "new.json", new)

    response = request(
        "/evaluation/compare?previous_run_id=previous&new_run_id=new",
        tmp_path,
    )

    assert response.status_code == 200
    assert response.json()["configuration_changes"] == [
        {"name": "top_k", "previous_value": 3, "new_value": 5}
    ]
    assert "secret" not in response.text


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_public_evaluation_endpoints_are_read_only(
    tmp_path: Path,
    method: str,
) -> None:
    response = request("/evaluation/runs", tmp_path, method=method)

    assert response.status_code == 405
