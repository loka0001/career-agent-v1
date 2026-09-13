"""Alembic migration environment."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context
from app.config import get_settings
from app.db import models as database_models
from app.db.base import Base
from app.db.session import (
    escape_alembic_config_value,
    normalize_database_url,
    normalize_migration_schema,
)

del database_models
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option(
    "sqlalchemy.url",
    escape_alembic_config_value(normalize_database_url(get_settings().database_url)),
)
target_metadata = Base.metadata
migration_schema = normalize_migration_schema(os.getenv("ALEMBIC_MIGRATION_SCHEMA"))


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(
            connection=supplied_connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            if connection.dialect.name == "postgresql":
                connection.execute(
                    text("SELECT set_config('search_path', :schema, true)"),
                    {"schema": migration_schema},
                )
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
