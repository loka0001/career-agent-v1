"""Engine and session factory creation."""

from __future__ import annotations

import re
from collections.abc import Iterator

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

VERIFICATION_SCHEMA_PATTERN = re.compile(r"verify_(?:empty|upgrade)_[0-9a-f]{12}")


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def normalize_migration_schema(value: str | None) -> str:
    """Allow only the application schema or verifier-generated disposable schemas."""

    schema = (value or "").strip() or "public"
    if schema == "public" or VERIFICATION_SCHEMA_PATTERN.fullmatch(schema):
        return schema
    raise ValueError("Invalid Alembic migration schema")


def escape_alembic_config_value(value: str) -> str:
    """Escape ConfigParser interpolation characters in runtime Alembic values."""

    return value.replace("%", "%%")


def _set_public_search_path(connection: Connection) -> None:
    """Pin each PostgreSQL transaction to the application schema."""

    connection.exec_driver_sql("SELECT set_config('search_path', 'public', true)")


def create_database_engine(
    database_url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 5,
    pool_recycle: int = 300,
) -> Engine:
    normalized_url = normalize_database_url(database_url)
    is_sqlite = normalized_url.startswith("sqlite")
    connect_args: dict[str, object] = {"check_same_thread": False} if is_sqlite else {}
    options: dict[str, object] = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "pool_recycle": pool_recycle,
    }
    if not is_sqlite:
        options.update(pool_size=pool_size, max_overflow=max_overflow, pool_timeout=15)
    engine = create_engine(normalized_url, **options)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        event.listen(engine, "begin", _set_public_search_path)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
