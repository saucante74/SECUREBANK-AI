from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings, settings
from app.core.rbac import Role

TOKEN_LIFETIME = timedelta(minutes=15)
TOKEN_SUBJECT = "securebank-development-user"


class DevelopmentTokenConfigurationError(Exception):
    pass


def generate_development_token(
    app_settings: Settings,
    issued_at: datetime | None = None,
) -> str:
    if (
        app_settings.jwt_secret_key is None
        or app_settings.jwt_issuer is None
        or app_settings.jwt_audience is None
    ):
        raise DevelopmentTokenConfigurationError(
            "JWT_SECRET_KEY, JWT_ISSUER and JWT_AUDIENCE are required"
        )

    token_issued_at = issued_at or datetime.now(UTC)
    return jwt.encode(
        {
            "sub": TOKEN_SUBJECT,
            "role": Role.ANALYST.value,
            "iat": token_issued_at,
            "exp": token_issued_at + TOKEN_LIFETIME,
            "iss": app_settings.jwt_issuer,
            "aud": app_settings.jwt_audience,
        },
        app_settings.jwt_secret_key.get_secret_value(),
        algorithm=app_settings.jwt_algorithm,
    )


def main() -> None:
    try:
        token = generate_development_token(settings)
    except DevelopmentTokenConfigurationError as error:
        raise SystemExit(str(error)) from error
    print(token)


if __name__ == "__main__":
    main()
