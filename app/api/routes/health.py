"""Cheap liveness and readiness probes."""

import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.dependencies import ContainerDependency
from app.api.schemas import ReadyResponse

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/health/live", response_model=ReadyResponse)
def live() -> ReadyResponse:
    return ReadyResponse(status="ok", checks={"process": True})


@router.get("/health/ready", response_model=ReadyResponse)
def ready(response: Response, container: ContainerDependency) -> ReadyResponse:
    checks = {"database": False, "search": False, "job_queue": False}
    try:
        with container.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("readiness_database_check_failed")
        checks["database"] = False
    try:
        checks["search"] = container.vector_store.ready()
    except Exception:
        logger.exception("readiness_search_check_failed")
        checks["search"] = False
    try:
        checks["job_queue"] = (
            container.job_queue.stale_running_count(
                stale_after_seconds=container.settings.worker_lease_seconds
            )
            == 0
        )
    except Exception:
        logger.exception("readiness_job_queue_check_failed")
        checks["job_queue"] = False
    all_ready = all(checks.values())
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="ok" if all_ready else "degraded", checks=checks)
