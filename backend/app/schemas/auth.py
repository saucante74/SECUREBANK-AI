from pydantic import BaseModel

from app.core.rbac import Role


class AuthenticatedIdentity(BaseModel):
    sub: str
    role: Role
