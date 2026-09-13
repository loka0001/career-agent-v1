"""Authenticated release operations executed inside the deployment environment."""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path
from typing import Annotated

from alembic.config import Config
from fastapi import APIRouter, Header
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command
from app.api.dependencies import ContainerDependency
from app.domain.errors import AuthenticationError, ConflictError, NotFoundError

router = APIRouter(prefix="/internal/release", tags=["release"])
LOCK_ID = 7_204_202_607_28


def _authorize(container: ContainerDependency, authorization: str | None) -> None:
    settings = container.settings
    secret = settings.cron_secret.get_secret_value()
    if settings.app_env not in {"staging", "production"} or len(secret) < 32:
        raise NotFoundError()
    expected = f"Bearer {secret}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise AuthenticationError("Invalid release authorization")


def _current_version(container: ContainerDependency) -> str | None:
    with container.engine.connect() as connection:
        return connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()


def _alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[3]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    return config


def _upgrade_connection(connection: Connection, schema: str, target: str) -> None:
    # Schema is generated from a hex token and never comes from request input.
    connection.execute(
        text("SELECT set_config('search_path', :schema, true)"),
        {"schema": schema},
    )
    config = _alembic_config()
    config.attributes["connection"] = connection
    command.upgrade(config, target)


@router.post("/migrate")
def migrate(
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, str | None]:
    _authorize(container, authorization)
    config = _alembic_config()
    before = _current_version(container)

    if container.engine.dialect.name == "postgresql":
        with container.engine.connect() as lock_connection:
            lock_connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": LOCK_ID})
            try:
                config.attributes["connection"] = lock_connection
                command.upgrade(config, "head")
                lock_connection.commit()
            except Exception:
                lock_connection.rollback()
                raise
            finally:
                config.attributes.pop("connection", None)
                if lock_connection.in_transaction():
                    lock_connection.rollback()
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": LOCK_ID}
                )
                lock_connection.commit()
    else:
        command.upgrade(config, "head")

    return {"status": "migrated", "before": before, "after": _current_version(container)}


@router.post("/verify-migrations")
def verify_migrations(
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, object]:
    """Prove clean and prior-schema upgrades without touching application tables."""

    _authorize(container, authorization)
    if container.engine.dialect.name != "postgresql":
        raise ConflictError("Migration verification requires PostgreSQL")
    suffix = secrets.token_hex(6)
    schemas = [f"verify_empty_{suffix}", f"verify_upgrade_{suffix}"]
    with container.engine.begin() as connection:
        for schema in schemas:
            connection.execute(CreateSchema(schema))
    try:
        with container.engine.begin() as connection:
            _upgrade_connection(connection, schemas[0], "head")
        with container.engine.begin() as connection:
            _upgrade_connection(connection, schemas[1], "20260728_0024")
            _upgrade_connection(connection, schemas[1], "head")
        return {
            "status": "verified",
            "clean_upgrade": "head",
            "prior_schema": "20260728_0024",
            "upgrade_path": "head",
        }
    finally:
        with container.engine.begin() as connection:
            for schema in schemas:
                connection.execute(DropSchema(schema, cascade=True, if_exists=True))
