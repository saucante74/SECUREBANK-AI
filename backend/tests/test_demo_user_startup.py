import asyncio
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.main as main_module
from app.core.config import Settings
from app.core.passwords import PasswordHasher
from app.core.rbac import Role
from app.main import app, initialize_demo_user, lifespan
from app.services.authentication import AuthenticationService, InvalidCredentialsError
from app.services.sessions import SQLiteSessionRepository
from app.services.users import SQLiteUserRepository, create_user_account

DEMO_USERNAME = "admin-demo"
DEMO_PASSWORD = "synthetic-demo-password"
LEGACY_USERNAME = "legacy.user@example.test"
LEGACY_PASSWORD = "synthetic-legacy-password"


def create_settings(database_path: Path, **updates: object) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        user_database_path=database_path,
        **updates,
    )


def create_authentication_service(settings: Settings) -> AuthenticationService:
    users = SQLiteUserRepository(settings.user_database_path)
    users.initialize()
    sessions = SQLiteSessionRepository(settings.user_database_path)
    sessions.initialize()
    return AuthenticationService(
        users,
        sessions,
        PasswordHasher(),
        settings.session_lifetime_seconds,
        settings.login_attempt_limit,
        settings.login_attempt_window_seconds,
    )


def test_lifespan_creates_hashed_demo_user_without_logging_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("DEMO_USER_USERNAME", DEMO_USERNAME)
    monkeypatch.setenv("DEMO_USER_PASSWORD", DEMO_PASSWORD)
    settings = Settings(
        _env_file=None,
        app_env="test",
        user_database_path=tmp_path / "users.sqlite3",
    )
    monkeypatch.setattr(main_module, "settings", settings)

    async def run_lifespan() -> None:
        async with lifespan(app):
            pass

    asyncio.run(run_lifespan())

    repository = SQLiteUserRepository(settings.user_database_path)
    account = repository.get_by_username(DEMO_USERNAME)
    stored_hash = repository.get_password_hash(DEMO_USERNAME)
    assert account is not None
    assert account.role is Role.ANALYST
    assert stored_hash is not None
    assert stored_hash != DEMO_PASSWORD
    assert PasswordHasher().verify(DEMO_PASSWORD, stored_hash)
    assert DEMO_PASSWORD not in caplog.text


def test_demo_user_can_log_in_and_rejects_wrong_password(tmp_path: Path) -> None:
    settings = create_settings(
        tmp_path / "users.sqlite3",
        demo_user_username=DEMO_USERNAME,
        demo_user_password=DEMO_PASSWORD,
    )
    initialize_demo_user(settings)
    authentication = create_authentication_service(settings)

    result = authentication.login(DEMO_USERNAME, DEMO_PASSWORD)

    assert result.identity.role is Role.ANALYST
    with pytest.raises(InvalidCredentialsError, match="Invalid credentials"):
        authentication.login(DEMO_USERNAME, "incorrect-password")


def test_demo_user_is_not_duplicated_or_changed_on_restart(tmp_path: Path) -> None:
    settings = create_settings(
        tmp_path / "users.sqlite3",
        demo_user_username=DEMO_USERNAME,
        demo_user_password=DEMO_PASSWORD,
    )
    initialize_demo_user(settings)
    repository = SQLiteUserRepository(settings.user_database_path)
    initial_hash = repository.get_password_hash(DEMO_USERNAME)

    initialize_demo_user(settings)

    with sqlite3.connect(settings.user_database_path) as connection:
        user_count = connection.execute(
            "SELECT COUNT(*) FROM users WHERE username = ? COLLATE NOCASE",
            (DEMO_USERNAME,),
        ).fetchone()[0]
    assert user_count == 1
    assert repository.get_password_hash(DEMO_USERNAME) == initial_hash


def test_missing_demo_configuration_preserves_current_behavior(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "users.sqlite3"

    initialize_demo_user(create_settings(database_path))

    assert not database_path.exists()


@pytest.mark.parametrize(
    "configured_value",
    [
        {"demo_user_username": DEMO_USERNAME},
        {"demo_user_password": DEMO_PASSWORD},
    ],
)
def test_partial_demo_configuration_fails_without_exposing_password(
    tmp_path: Path,
    configured_value: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="must be configured together") as error:
        create_settings(tmp_path / "users.sqlite3", **configured_value)

    assert DEMO_PASSWORD not in str(error.value)


def test_existing_email_identifier_remains_compatible(tmp_path: Path) -> None:
    settings = create_settings(tmp_path / "users.sqlite3")
    repository = SQLiteUserRepository(settings.user_database_path)
    repository.initialize()
    create_user_account(
        repository,
        PasswordHasher(),
        LEGACY_USERNAME,
        LEGACY_PASSWORD,
        Role.COMPLIANCE_OFFICER,
    )
    authentication = create_authentication_service(settings)

    result = authentication.login(LEGACY_USERNAME, LEGACY_PASSWORD)

    assert result.identity.role is Role.COMPLIANCE_OFFICER
