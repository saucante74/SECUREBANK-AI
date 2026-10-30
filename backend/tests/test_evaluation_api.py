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


def create_run(run_id: str, evidence_hit: float = 0.7) -> BaselineRun:
    return BaselineRun(
        benchmark_id="securebank-rag-retrieval-v1",
        run_id=run_id,
        created_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        code_version="a" * 40,
        rag_configuration={"top_k": 3, "strategy": "rrf"},
        parameter_change=None,
        measured_metrics={
            "RRF": {
                "source_hit_at_1": 0.6,
                "source_hit_at_3": 0.8,
                "evidence_hit_at_1": 0.5,
                "evidence_hit_at_3": evidence_hit,
                "mean_latency_seconds": 0.02,
            }
        },
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
    role: Role | None,
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
            return await client.get(path, headers=headers)

    try:
        return asyncio.run(send_request())
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_admin_can_list_and_read_runs(tmp_path: Path) -> None:
    write_run(tmp_path / "run.json", create_run("run-1"))

    listing = request("/evaluation/runs", tmp_path, Role.ADMIN)
    detail = request("/evaluation/runs/run-1", tmp_path, Role.ADMIN)

    assert listing.status_code == 200
    assert [run["run_id"] for run in listing.json()] == ["run-1"]
    assert detail.status_code == 200
    assert detail.json()["measured_metrics"]["RRF"]["evidence_hit_at_3"] == 0.7


@pytest.mark.parametrize("role", [Role.ANALYST, Role.COMPLIANCE_OFFICER])
def test_non_admin_roles_are_forbidden(tmp_path: Path, role: Role) -> None:
    response = request("/evaluation/runs", tmp_path, role)

    assert response.status_code == 403


def test_anonymous_user_is_rejected(tmp_path: Path) -> None:
    response = request("/evaluation/runs", tmp_path, None)

    assert response.status_code == 401


def test_missing_history_returns_an_empty_list(tmp_path: Path) -> None:
    response = request("/evaluation/runs", tmp_path / "missing", Role.ADMIN)

    assert response.status_code == 200
    assert response.json() == []


def test_invalid_history_is_not_exposed(tmp_path: Path) -> None:
    (tmp_path / "invalid.json").write_text(
        json.dumps({"run_id": "invalid", "secret": "must-not-leak"}),
        encoding="utf-8",
    )

    response = request("/evaluation/runs", tmp_path, Role.ADMIN)

    assert response.status_code == 503
    assert response.json() == {"detail": "Benchmark history is unavailable"}
    assert "must-not-leak" not in response.text


def test_unknown_run_returns_not_found(tmp_path: Path) -> None:
    response = request("/evaluation/runs/unknown", tmp_path, Role.ADMIN)

    assert response.status_code == 404


def test_admin_can_compare_configurations_and_each_engine(tmp_path: Path) -> None:
    previous = create_run("previous")
    new = create_run("new", evidence_hit=0.8).model_copy(
        update={"rag_configuration": {"top_k": 5, "strategy": "rrf"}}
    )
    write_run(tmp_path / "previous.json", previous)
    write_run(tmp_path / "new.json", new)

    response = request(
        "/evaluation/compare?previous_run_id=previous&new_run_id=new",
        tmp_path,
        Role.ADMIN,
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
