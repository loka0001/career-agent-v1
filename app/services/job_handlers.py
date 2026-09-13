"""Load every durable job handler required by the standalone worker."""

from __future__ import annotations

from importlib import import_module

from app.services.job_queue import JobHandler, registered_handlers

WORKER_HANDLER_MODULES = (
    "app.services.automations",
    "app.services.commerce_connectors",
    "app.services.content_studio",
    "app.services.conversations",
    "app.services.opportunities",
    "app.services.orders",
    "app.services.privacy",
    "app.api.routes.operations",
)

REQUIRED_WORKER_JOB_TYPES = frozenset(
    {
        "automation.execute",
        "channel.send_message",
        "commerce.sync",
        "content.generate_automation",
        "content.publish",
        "operations.diagnostic.retry_once",
        "operations.diagnostic.success",
        "opportunities.scan",
        "orders.repurchase_suggestion",
        "orders.review_request",
        "privacy.delete",
        "privacy.retention",
    }
)


def load_worker_job_handlers() -> dict[str, JobHandler]:
    """Import handler modules and fail closed if a required handler is absent."""

    for module_name in WORKER_HANDLER_MODULES:
        import_module(module_name)
    handlers = registered_handlers()
    missing = sorted(REQUIRED_WORKER_JOB_TYPES - handlers.keys())
    if missing:
        raise RuntimeError("Missing durable worker job handlers: " + ", ".join(missing))
    return handlers
