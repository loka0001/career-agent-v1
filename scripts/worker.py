"""Run the durable job queue as an independent worker process."""

from __future__ import annotations

import json
import logging
import signal
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app.config import Settings, get_settings
from app.container import AppContainer, build_container
from app.db.session import create_database_engine, create_session_factory
from app.services.job_handlers import load_worker_job_handlers
from app.services.job_queue import JobWorker

logger = logging.getLogger(__name__)


def health_response_status(path: str, health: dict[str, object]) -> HTTPStatus:
    if path == "/health/ready" and not health.get("ready"):
        return HTTPStatus.SERVICE_UNAVAILABLE
    return HTTPStatus.OK


def worker_runtime_preflight(settings: Settings) -> list[str]:
    """Return redacted production worker runtime blockers."""

    if settings.app_env != "production":
        return []
    issues: list[str] = []
    if not settings.enable_background_worker:
        issues.append("ENABLE_BACKGROUND_WORKER must be true for the persistent worker runtime")
    if settings.serverless_mode:
        issues.append("SERVERLESS_MODE/VERCEL must be false for the persistent worker runtime")
    database = urlparse(settings.database_url.replace("postgresql+psycopg", "postgresql", 1))
    if database.scheme not in {"postgres", "postgresql"}:
        issues.append("DATABASE_URL must use PostgreSQL for the production worker runtime")
    return issues


def _container() -> AppContainer:
    load_worker_job_handlers()
    settings = get_settings()
    preflight_issues = worker_runtime_preflight(settings)
    if preflight_issues:
        raise RuntimeError("Invalid worker runtime configuration: " + "; ".join(preflight_issues))
    engine = create_database_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle_seconds,
    )
    return build_container(settings, engine, create_session_factory(engine))


def main() -> None:
    container = _container()
    settings = container.settings
    worker = JobWorker(container.job_queue, poll_seconds=settings.worker_poll_seconds)

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/health", "/health/live", "/health/ready"}:
                self.send_error(404)
                return
            health = worker.health()
            response_status = health_response_status(self.path, health)
            payload = json.dumps(health, separators=(",", ":")).encode()
            self.send_response(response_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            logger.debug("worker_health_request", extra={"message": format % args})

    health_server = ThreadingHTTPServer(("0.0.0.0", settings.worker_health_port), HealthHandler)
    health_thread = threading.Thread(
        target=health_server.serve_forever,
        name="worker-health",
        daemon=True,
    )
    health_thread.start()

    def shutdown(_signum: int, _frame: object) -> None:
        worker.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        worker.run_forever()
    finally:
        health_server.shutdown()
        health_server.server_close()
        container.engine.dispose()


if __name__ == "__main__":
    main()
