"""Create and seed a fresh local SQLite database without production migrations."""

from __future__ import annotations

import json

from app.config import get_settings
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.db.seed import seed_database
from app.db.session import create_database_engine, create_session_factory
from app.integrations.sql_search_store import SQLSearchStore


def main() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        raise RuntimeError("Local schema initialization is disabled in production")
    if not settings.database_url.startswith("sqlite"):
        raise RuntimeError(
            "scripts.init_local is only for a fresh local SQLite database; "
            "use Alembic migrations for PostgreSQL"
        )
    if not settings.demo_mode:
        raise RuntimeError("Set DEMO_MODE=true before initializing the local demo")

    engine = create_database_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle_seconds,
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    result = seed_database(settings, factory, SQLSearchStore(factory))
    print(
        json.dumps(
            {
                "status": "ready",
                "database": settings.database_url,
                "seed": result,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
