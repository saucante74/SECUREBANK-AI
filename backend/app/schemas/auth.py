from pydantic import BaseModel


class AuthenticatedIdentity(BaseModel):
    sub: str
