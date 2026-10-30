from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_settings, require_roles
from app.core.config import Settings
from app.core.rbac import Role
from app.schemas.auth import AuthenticatedIdentity
from app.services.baseline_history import (
    BaselineComparison,
    BaselineHistoryError,
    BaselineRun,
    BaselineRunNotFoundError,
    compare_baseline_runs,
    get_baseline_run,
    load_baseline_runs,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
AdminIdentity = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(Role.ADMIN)),
]


def history_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Benchmark history is unavailable",
    )


@router.get("/runs", response_model=list[BaselineRun])
def list_runs(
    _identity: AdminIdentity,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[BaselineRun]:
    try:
        return load_baseline_runs(settings.benchmark_results_path)
    except BaselineHistoryError:
        raise history_error() from None


@router.get("/runs/{run_id}", response_model=BaselineRun)
def read_run(
    run_id: str,
    _identity: AdminIdentity,
    settings: Annotated[Settings, Depends(get_settings)],
) -> BaselineRun:
    try:
        return get_baseline_run(run_id, settings.benchmark_results_path)
    except BaselineRunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        ) from None
    except BaselineHistoryError:
        raise history_error() from None


@router.get("/compare", response_model=BaselineComparison)
def compare_runs(
    previous_run_id: Annotated[str, Query(min_length=1, max_length=100)],
    new_run_id: Annotated[str, Query(min_length=1, max_length=100)],
    _identity: AdminIdentity,
    settings: Annotated[Settings, Depends(get_settings)],
) -> BaselineComparison:
    try:
        previous = get_baseline_run(
            previous_run_id,
            settings.benchmark_results_path,
        )
        new = get_baseline_run(new_run_id, settings.benchmark_results_path)
        return compare_baseline_runs(previous, new)
    except BaselineRunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        ) from None
    except BaselineHistoryError:
        raise history_error() from None
