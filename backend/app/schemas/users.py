from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.rbac import Role


class UserAccount(BaseModel):
    id: UUID
    username: str
    role: Role
    is_active: bool

    model_config = ConfigDict(frozen=True)
