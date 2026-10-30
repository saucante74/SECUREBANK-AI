import sqlite3
from pathlib import Path

import pytest

from app.core.passwords import PasswordHasher, PasswordPolicyError
from app.core.rbac import Role
from app.services.users import (
    InvalidUsernameError,
    SQLiteUserRepository,
    UserAlreadyExistsError,
    create_user_account,
)

TEST_PASSWORD = "synthetic-password-42"


def create_repository(database_path: Path) -> SQLiteUserRepository:
    repository = SQLiteUserRepository(database_path)
    repository.initialize()
    return repository


def test_user_is_persisted_with_hashed_password(tmp_path: Path) -> None:
    database_path = tmp_path / "users.sqlite3"
    repository = create_repository(database_path)
    password_hasher = PasswordHasher()

    created = create_user_account(
        repository,
        password_hasher,
        " Demo.Analyst ",
        TEST_PASSWORD,
        Role.ANALYST,
    )
    reloaded = SQLiteUserRepository(database_path).get_by_username("DEMO.ANALYST")
    stored_hash = repository.get_password_hash("demo.analyst")

    assert reloaded == created
    assert stored_hash is not None
    assert stored_hash != TEST_PASSWORD
    assert password_hasher.verify(TEST_PASSWORD, stored_hash)
    assert not password_hasher.verify("incorrect-password", stored_hash)


def test_user_persists_after_repository_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "users.sqlite3"
    repository = create_repository(database_path)
    created = create_user_account(
        repository,
        PasswordHasher(),
        "persistent-user",
        TEST_PASSWORD,
        Role.COMPLIANCE_OFFICER,
        is_active=False,
    )

    restarted_repository = create_repository(database_path)

    assert restarted_repository.get_by_username("persistent-user") == created
    assert created.is_active is False


def test_duplicate_username_is_rejected_case_insensitively(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "users.sqlite3")
    password_hasher = PasswordHasher()
    create_user_account(
        repository,
        password_hasher,
        "unique-user",
        TEST_PASSWORD,
        Role.ADMIN,
    )

    with pytest.raises(UserAlreadyExistsError):
        create_user_account(
            repository,
            password_hasher,
            "UNIQUE-USER",
            TEST_PASSWORD,
            Role.ANALYST,
        )


@pytest.mark.parametrize("username", ["", "   ", "invalid user", "x" * 101])
def test_invalid_username_is_rejected(tmp_path: Path, username: str) -> None:
    repository = create_repository(tmp_path / "users.sqlite3")

    with pytest.raises(InvalidUsernameError):
        create_user_account(
            repository,
            PasswordHasher(),
            username,
            TEST_PASSWORD,
            Role.ANALYST,
        )


@pytest.mark.parametrize("password", ["short", "é" * 37])
def test_invalid_password_is_rejected(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        PasswordHasher().hash(password)


def test_database_rejects_an_unknown_role(tmp_path: Path) -> None:
    database_path = tmp_path / "users.sqlite3"
    create_repository(database_path)

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (id, username, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("synthetic-id", "invalid-role", "synthetic-hash", "unknown", 1),
            )
