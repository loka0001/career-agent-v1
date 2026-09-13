from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.verify_all as verify_all


class _RecordingCursor:
    def __enter__(self) -> _RecordingCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str) -> None:
        del query


class _RecordingConnection:
    def __enter__(self) -> _RecordingConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> _RecordingCursor:
        return _RecordingCursor()


def test_migration_gate_overrides_demo_only_dotenv_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environments: list[dict[str, str]] = []
    monkeypatch.setenv("ENABLE_FAKE_PUBLISHING", "true")
    monkeypatch.setenv("BILLING_PROVIDER", "demo")
    monkeypatch.setenv("PAYMENT_PROVIDER", "demo")
    monkeypatch.setattr(
        verify_all.psycopg,
        "connect",
        lambda *args, **kwargs: _RecordingConnection(),
    )
    monkeypatch.setattr(
        verify_all,
        "run",
        lambda command, *, env=None, **kwargs: environments.append(dict(env or {})),
    )
    monkeypatch.setattr(
        verify_all,
        "secrets",
        SimpleNamespace(token_hex=lambda _: "abcdefabcdef"),
    )

    verify_all.migration_gate("postgresql://postgres@localhost/postgres")

    assert len(environments) == 3
    for environment in environments:
        assert environment["DEMO_MODE"] == "false"
        assert environment["ENABLE_FAKE_PUBLISHING"] == "false"
        assert environment["BILLING_PROVIDER"] == "disabled"
        assert environment["PAYMENT_PROVIDER"] == "cod"
    assert environments[0]["ALEMBIC_MIGRATION_SCHEMA"] == "verify_empty_abcdefabcdef"
    assert environments[1]["ALEMBIC_MIGRATION_SCHEMA"] == "verify_upgrade_abcdefabcdef"
    assert environments[2]["ALEMBIC_MIGRATION_SCHEMA"] == "verify_upgrade_abcdefabcdef"


def test_verify_all_runs_deployment_smoke_when_url_is_supplied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def record_run(
        command: list[str],
        *,
        cwd: Path = verify_all.ROOT,
        env: dict[str, str] | None = None,
    ) -> None:
        del cwd
        if (
            command[:3] == [sys.executable, "-m", "ruff"]
            or command[:3]
            == [
                sys.executable,
                "-m",
                "mypy",
            ]
            or command[:3] == [sys.executable, "-m", "pytest"]
        ):
            assert env is not None
            assert env["PYTHONDONTWRITEBYTECODE"] == "1"
            assert env["RUFF_NO_CACHE"] == "true"
        commands.append(command)

    release_secret = tmp_path / "release-secret.txt"
    release_secret.write_text("s" * 48, encoding="utf-8")
    monkeypatch.setattr(verify_all, "run", record_run)
    monkeypatch.setattr(verify_all, "remote_migration_gate", lambda endpoint, secret_file: None)
    monkeypatch.setattr(verify_all, "fresh_frontend_gate", lambda: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_all.py",
            "--migration-endpoint",
            "https://commerce.example.com/api/v1/internal/release/verify-migrations",
            "--release-secret-file",
            str(release_secret),
            "--deployment-url",
            "https://commerce.example.com",
        ],
    )

    assert verify_all.main() == 0

    assert [
        sys.executable,
        "scripts/verify_deployment_smoke.py",
        "https://commerce.example.com",
    ] in commands
    assert [
        sys.executable,
        "-m",
        "mypy",
        "--strict",
        "--cache-dir",
        str(verify_all.MYPY_CACHE),
        "app",
        "scripts",
    ] in commands
    assert [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"] in commands
    assert [sys.executable, "scripts/verify_environment_matrix.py"] in commands
    assert [sys.executable, "scripts/verify_env_example.py"] in commands
    assert [sys.executable, "scripts/verify_production_access.py"] in commands
    assert [sys.executable, "scripts/verify_vercel_access_evidence.py"] in commands
    assert [sys.executable, "scripts/verify_operations_runbook.py"] in commands
    assert [sys.executable, "scripts/verify_repository_handoff_manifest.py"] in commands


def test_verify_all_skips_deployment_smoke_without_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    release_secret = tmp_path / "release-secret.txt"
    release_secret.write_text("s" * 48, encoding="utf-8")
    monkeypatch.setattr(verify_all, "run", lambda command, **_: commands.append(command))
    monkeypatch.setattr(verify_all, "remote_migration_gate", lambda endpoint, secret_file: None)
    monkeypatch.setattr(verify_all, "fresh_frontend_gate", lambda: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_all.py",
            "--migration-endpoint",
            "https://commerce.example.com/api/v1/internal/release/verify-migrations",
            "--release-secret-file",
            str(release_secret),
        ],
    )

    assert verify_all.main() == 0

    assert not any("scripts/verify_deployment_smoke.py" in command for command in commands)
    assert [
        sys.executable,
        "-m",
        "mypy",
        "--strict",
        "--cache-dir",
        str(verify_all.MYPY_CACHE),
        "app",
        "scripts",
    ] in commands
    assert [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"] in commands
    assert [sys.executable, "scripts/verify_environment_matrix.py"] in commands
    assert [sys.executable, "scripts/verify_env_example.py"] in commands
    assert [sys.executable, "scripts/verify_production_access.py"] in commands
    assert [sys.executable, "scripts/verify_vercel_access_evidence.py"] in commands
    assert [sys.executable, "scripts/verify_operations_runbook.py"] in commands
    assert [sys.executable, "scripts/verify_repository_handoff_manifest.py"] in commands
