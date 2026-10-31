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
from app.services.baseline_history import BaselineRun

JWT_SECRET = "synthetic-evaluation-secret-key-with-at-least-32-characters"
JWT_ISSUER = "securebank-ai-evaluation-test"
JWT_AUDIENCE = "securebank-ai-evaluation-api"


def create_run(
    run_id: str,
    evidence_hit: float = 0.7,
    include_operational_metrics: bool = False,
) -> BaselineRun:
    metrics = {
        "source_hit_at_1": 0.6,
        "source_hit_at_3": 0.8,
        "evidence_hit_at_1": 0.5,
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
        benchmark_id="securebank-rag-retrieval-v1",
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
