import sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.passwords import PasswordHasher
from app.core.rbac import Role
from app.schemas.users import UserAccount


class UserAlreadyExistsError(Exception):
    pass


class InvalidUsernameError(ValueError):
    pass


@dataclass(frozen=True)
class UserCredentials:
    account: UserAccount
    password_hash: str


class SQLiteUserRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (
                        role IN ('analyst', 'compliance_officer', 'admin')
                    ),
                    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
                )
                """
            )

    def create(
        self,
        username: str,
        password_hash: str,
        role: Role,
        is_active: bool = True,
    ) -> UserAccount:
        normalized_username = normalize_username(username)
        account = UserAccount(
            id=uuid4(),
            username=normalized_username,
            role=role,
            is_active=is_active,
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users (id, username, password_hash, role, is_active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(account.id),
                        account.username,
                        password_hash,
                        account.role.value,
                        int(account.is_active),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise UserAlreadyExistsError("User already exists") from error
        return account

    def get_by_username(self, username: str) -> UserAccount | None:
        normalized_username = normalize_username(username)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, role, is_active
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (normalized_username,),
            ).fetchone()
        if row is None:
            return None
        return UserAccount(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )

    def get_password_hash(self, username: str) -> str | None:
        normalized_username = normalize_username(username)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ? COLLATE NOCASE",
                (normalized_username,),
            ).fetchone()
        return None if row is None else str(row["password_hash"])

    def get_credentials(self, username: str) -> UserCredentials | None:
        normalized_username = normalize_username(username)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, role, is_active
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (normalized_username,),
            ).fetchone()
        if row is None:
            return None
        return UserCredentials(
            account=UserAccount(
                id=row["id"],
                username=row["username"],
                role=row["role"],
                is_active=bool(row["is_active"]),
            ),
            password_hash=row["password_hash"],
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection


def create_user_account(
    repository: SQLiteUserRepository,
    password_hasher: PasswordHasher,
    username: str,
    password: str,
    role: Role,
    is_active: bool = True,
) -> UserAccount:
    normalized_username = normalize_username(username)
    password_hash = password_hasher.hash(password)
    return repository.create(normalized_username, password_hash, role, is_active)


def normalize_username(username: str) -> str:
    normalized_username = username.strip().lower()
    if not normalized_username or len(normalized_username) > 100:
        raise InvalidUsernameError("Username must contain between 1 and 100 characters")
    if any(character.isspace() for character in normalized_username):
        raise InvalidUsernameError("Username must not contain whitespace")
    return normalized_username
