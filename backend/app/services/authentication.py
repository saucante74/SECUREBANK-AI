from dataclasses import dataclass

from app.core.passwords import PasswordHasher
from app.schemas.auth import AuthenticatedIdentity
from app.services.sessions import CreatedSession, SQLiteSessionRepository
from app.services.users import InvalidUsernameError, SQLiteUserRepository


class InvalidCredentialsError(Exception):
    pass


class LoginRateLimitError(Exception):
    pass


@dataclass(frozen=True)
class LoginResult:
    identity: AuthenticatedIdentity
    session: CreatedSession


class AuthenticationService:
    def __init__(
        self,
        user_repository: SQLiteUserRepository,
        session_repository: SQLiteSessionRepository,
        password_hasher: PasswordHasher,
        session_lifetime_seconds: int,
        login_attempt_limit: int,
        login_attempt_window_seconds: int,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._passwords = password_hasher
        self._session_lifetime_seconds = session_lifetime_seconds
        self._login_attempt_limit = login_attempt_limit
        self._login_attempt_window_seconds = login_attempt_window_seconds

    def login(self, username: str, password: str) -> LoginResult:
        normalized_username = username.strip().lower()
        if self._sessions.is_login_limited(
            normalized_username,
            self._login_attempt_limit,
            self._login_attempt_window_seconds,
        ):
            raise LoginRateLimitError("Too many login attempts")

        try:
            credentials = self._users.get_credentials(normalized_username)
        except InvalidUsernameError:
            credentials = None

        if credentials is None:
            self._passwords.consume_verification_time(password)
            self._record_failure(normalized_username)
            raise InvalidCredentialsError("Invalid credentials")

        valid_password = self._passwords.verify(password, credentials.password_hash)
        if not valid_password or not credentials.account.is_active:
            self._record_failure(normalized_username)
            raise InvalidCredentialsError("Invalid credentials")

        self._sessions.clear_login_failures(normalized_username)
        session = self._sessions.create(
            str(credentials.account.id),
            self._session_lifetime_seconds,
        )
        identity = AuthenticatedIdentity(
            sub=str(credentials.account.id),
            role=credentials.account.role,
        )
        return LoginResult(identity, session)

    def _record_failure(self, username: str) -> None:
        self._sessions.record_login_failure(
            username,
            self._login_attempt_window_seconds,
        )
