import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.api.dependencies import get_settings
from app.core.config import Settings
from app.core.passwords import PasswordHasher
from app.core.rbac import Role
from app.main import app
from app.services.sessions import SQLiteSessionRepository
from app.services.users import SQLiteUserRepository, create_user_account

TEST_ORIGIN = "http://test"
TEST_PASSWORD = "synthetic-session-password"
LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
)


def create_test_settings(database_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        user_database_path=database_path,
        auth_trusted_origins=TEST_ORIGIN,
        login_attempt_limit=2,
        login_attempt_window_seconds=60,
    )


def create_user(
    settings: Settings,
    username: str = "session-user",
    role: Role = Role.ANALYST,
    is_active: bool = True,
) -> None:
    repository = SQLiteUserRepository(settings.user_database_path)
    repository.initialize()
    create_user_account(
        repository,
        PasswordHasher(),
        username,
        TEST_PASSWORD,
        role,
        is_active,
    )


def run_session_scenario(
    settings: Settings,
    scenario: object,
) -> object:
    def override_settings() -> Settings:
        return settings

    app.dependency_overrides[get_settings] = override_settings
    try:
        return asyncio.run(scenario)
    finally:
        app.dependency_overrides.pop(get_settings)


def test_login_sets_session_and_allows_auth_me(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> tuple[Response, Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            login_response = await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )
            me_response = await client.get("/auth/me")
            return login_response, me_response

    login_response, me_response = run_session_scenario(settings, scenario())

    assert login_response.status_code == 200
    assert login_response.json()["role"] == "analyst"
    assert me_response.status_code == 200
    assert me_response.json() == login_response.json()
    cookies = login_response.headers.get_list("set-cookie")
    assert any(
        "securebank_session=" in cookie and "HttpOnly" in cookie for cookie in cookies
    )
    assert any(
        "securebank_csrf=" in cookie and "HttpOnly" not in cookie for cookie in cookies
    )
    assert all("SameSite=lax" in cookie for cookie in cookies)
    assert all("Secure" not in cookie for cookie in cookies)
    assert all("Path=/" in cookie for cookie in cookies)
    assert all("Domain=" not in cookie for cookie in cookies)


def test_admin_session_restores_evaluation_access_and_logs_out(
    tmp_path: Path,
) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3").model_copy(
        update={"benchmark_results_path": tmp_path / "benchmark_results"}
    )
    create_user(settings, role=Role.ADMIN)

    async def scenario() -> tuple[Response, Response, Response, Response, Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            anonymous_me = await client.get("/auth/me")
            login_response = await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )
            restored_me = await client.get("/auth/me")
            evaluation_response = await client.get("/evaluation/runs")
            csrf_token = client.cookies.get("securebank_csrf")
            await client.post(
                "/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )
            logged_out_me = await client.get("/auth/me")
            return (
                anonymous_me,
                login_response,
                restored_me,
                evaluation_response,
                logged_out_me,
            )

    result = run_session_scenario(settings, scenario())

    assert isinstance(result, tuple)
    anonymous_me, login_response, restored_me, evaluation_response, logged_out_me = (
        result
    )
    assert anonymous_me.status_code == 401
    assert login_response.status_code == 200
    assert login_response.json()["role"] == "admin"
    assert restored_me.status_code == 200
    assert restored_me.json()["role"] == "admin"
    assert evaluation_response.status_code == 200
    assert logged_out_me.status_code == 401


def test_secure_cookie_is_enabled_by_configuration(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3").model_copy(
        update={"session_cookie_secure": True, "session_cookie_samesite": "none"}
    )
    create_user(settings)

    async def scenario() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )

    response = run_session_scenario(settings, scenario())

    assert isinstance(response, Response)
    assert all("Secure" in cookie for cookie in response.headers.get_list("set-cookie"))
    assert all(
        "SameSite=none" in cookie for cookie in response.headers.get_list("set-cookie")
    )


def test_login_accepts_each_local_frontend_origin(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3").model_copy(
        update={"auth_trusted_origins": ",".join(LOCAL_FRONTEND_ORIGINS)}
    )
    create_user(settings)

    async def scenario() -> list[Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return [
                await client.post(
                    "/auth/login",
                    headers={"Origin": origin},
                    json={"username": "session-user", "password": TEST_PASSWORD},
                )
                for origin in LOCAL_FRONTEND_ORIGINS
            ]

    responses = run_session_scenario(settings, scenario())

    assert isinstance(responses, list)
    assert [response.status_code for response in responses] == [200, 200, 200, 200]


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("session-user", "wrong-password"),
        ("unknown-user", "wrong-password"),
    ],
)
def test_login_rejects_invalid_credentials_with_generic_error(
    tmp_path: Path,
    username: str,
    password: str,
) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": username, "password": password},
            )

    response = run_session_scenario(settings, scenario())

    assert isinstance(response, Response)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}
    assert "set-cookie" not in response.headers


def test_login_rejects_disabled_account_with_same_error(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings, is_active=False)

    async def scenario() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )

    response = run_session_scenario(settings, scenario())

    assert isinstance(response, Response)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_requires_trusted_origin(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return await client.post(
                "/auth/login",
                headers={"Origin": "https://untrusted.example"},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )

    response = run_session_scenario(settings, scenario())

    assert isinstance(response, Response)
    assert response.status_code == 403
    assert response.json() == {"detail": "Request origin is not allowed"}


def test_cookie_logout_requires_csrf_and_invalidates_session(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> tuple[Response, Response, Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )
            rejected_logout = await client.post("/auth/logout")
            csrf_token = client.cookies.get("securebank_csrf")
            accepted_logout = await client.post(
                "/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )
            me_response = await client.get("/auth/me")
            return rejected_logout, accepted_logout, me_response

    rejected_logout, accepted_logout, me_response = run_session_scenario(
        settings,
        scenario(),
    )

    assert rejected_logout.status_code == 403
    assert rejected_logout.json() == {"detail": "CSRF validation failed"}
    assert accepted_logout.status_code == 204
    assert me_response.status_code == 401


def test_expired_session_is_deleted(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)
    users = SQLiteUserRepository(settings.user_database_path)
    account = users.get_by_username("session-user")
    assert account is not None
    sessions = SQLiteSessionRepository(settings.user_database_path)
    sessions.initialize()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    session = sessions.create(str(account.id), 60, now)

    identity = sessions.resolve(session.session_token, now + timedelta(seconds=60))

    assert identity is None
    assert sessions.resolve(session.session_token, now) is None


def test_login_is_rate_limited_after_repeated_failures(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> list[Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            return [
                await client.post(
                    "/auth/login",
                    headers={"Origin": TEST_ORIGIN},
                    json={"username": "session-user", "password": "wrong-password"},
                )
                for _ in range(3)
            ]

    responses = run_session_scenario(settings, scenario())

    assert isinstance(responses, list)
    assert [response.status_code for response in responses] == [401, 401, 429]


def test_cookie_identity_preserves_rbac_restrictions(tmp_path: Path) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings, role=Role.ANALYST)

    async def scenario() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )
            return await client.get("/auth/admin")

    response = run_session_scenario(settings, scenario())

    assert isinstance(response, Response)
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_rag_remains_protected_and_requires_csrf_for_cookie_session(
    tmp_path: Path,
) -> None:
    settings = create_test_settings(tmp_path / "users.sqlite3")
    create_user(settings)

    async def scenario() -> tuple[Response, Response]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=TEST_ORIGIN) as client:
            await client.post(
                "/auth/login",
                headers={"Origin": TEST_ORIGIN},
                json={"username": "session-user", "password": TEST_PASSWORD},
            )
            rejected_request = await client.post(
                "/rag/ask",
                json={"question": "Synthetic regulatory question"},
            )
            csrf_token = client.cookies.get("securebank_csrf")
            authenticated_request = await client.post(
                "/rag/ask",
                headers={"X-CSRF-Token": csrf_token},
                json={"question": "Synthetic regulatory question"},
            )
            return rejected_request, authenticated_request

    rejected_request, authenticated_request = run_session_scenario(
        settings,
        scenario(),
    )

    assert rejected_request.status_code == 403
    assert rejected_request.json() == {"detail": "CSRF validation failed"}
    assert authenticated_request.status_code == 503
    assert authenticated_request.json() == {"detail": "RAG pipeline is not configured"}
