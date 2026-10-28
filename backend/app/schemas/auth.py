from pydantic import BaseModel, SecretStr, field_validator

from app.core.rbac import Role


class AuthenticatedIdentity(BaseModel):
    sub: str
    role: Role


class LoginRequest(BaseModel):
    username: str
    password: SecretStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if not normalized_value or len(normalized_value) > 100:
            raise ValueError("Invalid credentials")
        return normalized_value
