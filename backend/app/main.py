from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.evaluation import router as evaluation_router
from app.api.pii import router as pii_router
from app.api.rag import router as rag_router
from app.core.config import Settings, settings
from app.core.passwords import PasswordHasher
from app.core.rbac import Role
from app.services.users import SQLiteUserRepository, create_user_account_if_missing


def initialize_demo_user(app_settings: Settings) -> None:
    if (
        app_settings.demo_user_username is None
        or app_settings.demo_user_password is None
    ):
        return
    repository = SQLiteUserRepository(app_settings.user_database_path)
    repository.initialize()
    create_user_account_if_missing(
        repository,
        PasswordHasher(),
        app_settings.demo_user_username,
        app_settings.demo_user_password.get_secret_value(),
        Role.ANALYST,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    initialize_demo_user(settings)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(evaluation_router)
app.include_router(pii_router)
app.include_router(rag_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
