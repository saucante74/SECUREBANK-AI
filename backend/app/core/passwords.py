import bcrypt

MINIMUM_PASSWORD_LENGTH = 12
MAXIMUM_PASSWORD_BYTES = 72


class PasswordPolicyError(ValueError):
    pass


class PasswordHasher:
    def hash(self, password: str) -> str:
        self._validate(password)
        password_bytes = password.encode("utf-8")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (TypeError, ValueError, UnicodeEncodeError):
            return False

    def _validate(self, password: str) -> None:
        if len(password) < MINIMUM_PASSWORD_LENGTH:
            raise PasswordPolicyError(
                f"Password must contain at least {MINIMUM_PASSWORD_LENGTH} characters"
            )
        if len(password.encode("utf-8")) > MAXIMUM_PASSWORD_BYTES:
            raise PasswordPolicyError(
                f"Password must not exceed {MAXIMUM_PASSWORD_BYTES} UTF-8 bytes"
            )
