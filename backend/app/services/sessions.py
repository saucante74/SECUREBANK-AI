import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.schemas.auth import AuthenticatedIdentity


@dataclass(frozen=True)
class CreatedSession:
    session_token: str
    csrf_token: str
    expires_at: datetime


class SQLiteSessionRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    csrf_hash TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    failure_count INTEGER NOT NULL,
                    window_started_at INTEGER NOT NULL
                )
                """
            )

    def create(
        self,
        user_id: str,
        lifetime_seconds: int,
        now: datetime | None = None,
    ) -> CreatedSession:
        current_time = now or datetime.now(UTC)
        expires_at = current_time + timedelta(seconds=lifetime_seconds)
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (session_hash, user_id, csrf_hash, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    hash_token(session_token),
                    user_id,
                    hash_token(csrf_token),
                    int(expires_at.timestamp()),
                ),
            )
        return CreatedSession(session_token, csrf_token, expires_at)

    def resolve(
        self,
        session_token: str,
        now: datetime | None = None,
    ) -> AuthenticatedIdentity | None:
        current_timestamp = int((now or datetime.now(UTC)).timestamp())
        session_hash = hash_token(session_token)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.role, users.is_active, sessions.expires_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.session_hash = ?
                """,
                (session_hash,),
            ).fetchone()
            if row is None:
                return None
            if not bool(row["is_active"]) or row["expires_at"] <= current_timestamp:
                connection.execute(
                    "DELETE FROM sessions WHERE session_hash = ?",
                    (session_hash,),
                )
                return None
        return AuthenticatedIdentity(sub=row["id"], role=row["role"])

    def validate_csrf(self, session_token: str, csrf_token: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT csrf_hash FROM sessions WHERE session_hash = ?",
                (hash_token(session_token),),
            ).fetchone()
        if row is None:
            return False
        return hmac.compare_digest(str(row["csrf_hash"]), hash_token(csrf_token))

    def delete(self, session_token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE session_hash = ?",
                (hash_token(session_token),),
            )

    def is_login_limited(
        self,
        username: str,
        attempt_limit: int,
        window_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        current_timestamp = int((now or datetime.now(UTC)).timestamp())
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT failure_count, window_started_at
                FROM login_attempts
                WHERE username = ? COLLATE NOCASE
                """,
                (username,),
            ).fetchone()
            if row is None:
                return False
            if current_timestamp - row["window_started_at"] >= window_seconds:
                connection.execute(
                    "DELETE FROM login_attempts WHERE username = ? COLLATE NOCASE",
                    (username,),
                )
                return False
        return bool(row["failure_count"] >= attempt_limit)

    def record_login_failure(
        self,
        username: str,
        window_seconds: int,
        now: datetime | None = None,
    ) -> None:
        current_timestamp = int((now or datetime.now(UTC)).timestamp())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT failure_count, window_started_at
                FROM login_attempts
                WHERE username = ? COLLATE NOCASE
                """,
                (username,),
            ).fetchone()
            if (
                row is None
                or current_timestamp - row["window_started_at"] >= window_seconds
            ):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO login_attempts
                        (username, failure_count, window_started_at)
                    VALUES (?, 1, ?)
                    """,
                    (username, current_timestamp),
                )
            else:
                connection.execute(
                    """
                    UPDATE login_attempts
                    SET failure_count = failure_count + 1
                    WHERE username = ? COLLATE NOCASE
                    """,
                    (username,),
                )

    def clear_login_failures(self, username: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM login_attempts WHERE username = ? COLLATE NOCASE",
                (username,),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
