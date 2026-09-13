"""Database engine configuration tests."""

from typing import Any

import pytest

from app.db import session as db_session


def test_postgres_engine_forces_public_search_path(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}
    expected_engine = object()

    def fake_create_engine(url: str, **options: object) -> object:
        captured["url"] = url
        captured["options"] = options
        return expected_engine

    def fake_event_listen(target: object, name: str, callback: object) -> None:
        captured["event"] = (target, name, callback)

    monkeypatch.setattr(db_session, "create_engine", fake_create_engine)
    monkeypatch.setattr(db_session.event, "listen", fake_event_listen)

    engine = db_session.create_database_engine(
        "postgresql://example.test/commerce?sslmode=require",
        pool_size=3,
        max_overflow=4,
        pool_recycle=120,
    )

    assert engine is expected_engine
    assert captured["url"] == ("postgresql+psycopg://example.test/commerce?sslmode=require")
    options = captured["options"]
    assert isinstance(options, dict)
    assert options["connect_args"] == {}
    assert options["pool_size"] == 3
    assert options["max_overflow"] == 4
    assert options["pool_recycle"] == 120
    assert captured["event"] == (
        expected_engine,
        "begin",
        db_session._set_public_search_path,
    )


def test_public_search_path_is_transaction_local() -> None:
    statements: list[str] = []

    class FakeConnection:
        def exec_driver_sql(self, statement: str) -> None:
            statements.append(statement)

    db_session._set_public_search_path(FakeConnection())  # type: ignore[arg-type]

    assert statements == ["SELECT set_config('search_path', 'public', true)"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "public"),
        ("", "public"),
        ("public", "public"),
        ("verify_empty_012345abcdef", "verify_empty_012345abcdef"),
        ("verify_upgrade_fedcba543210", "verify_upgrade_fedcba543210"),
    ],
)
def test_migration_schema_accepts_only_public_or_generated_verification_names(
    value: str | None, expected: str
) -> None:
    assert db_session.normalize_migration_schema(value) == expected


@pytest.mark.parametrize(
    "value",
    ["tenant", "verify_empty_bad", "verify_empty_012345abcdef,public", 'public"'],
)
def test_migration_schema_rejects_untrusted_search_paths(value: str) -> None:
    with pytest.raises(ValueError, match="migration schema"):
        db_session.normalize_migration_schema(value)


def test_alembic_config_value_escapes_percent_encoded_database_urls() -> None:
    assert (
        db_session.escape_alembic_config_value(
            "postgresql+psycopg://example.test/database?application_name=release%20gate"
        )
        == "postgresql+psycopg://example.test/database?application_name=release%%20gate"
    )
