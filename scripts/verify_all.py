"""Run the reproducible backend, PostgreSQL migration, frontend, and release gates."""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MYPY_CACHE = ROOT.parent / ".tools" / "mypy-cache-commerce-ai"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"\n> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def npm_command() -> str:
    portable = ROOT.parent / ".tools" / "node24" / ("npm.cmd" if os.name == "nt" else "npm")
    if portable.is_file():
        return str(portable)
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if executable:
        return executable
    raise RuntimeError("Node.js 24 and npm are required")


def release_tool_env() -> dict[str, str]:
    """Keep verification tool caches and bytecode out of the source tree."""

    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "RUFF_NO_CACHE": "true",
    }


def postgres_url() -> str:
    value = os.getenv("VERIFY_POSTGRES_URL", "").strip()
    if not value:
        candidate = os.getenv("DATABASE_URL", "").strip()
        if candidate.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            value = candidate
    if not value:
        raise RuntimeError(
            "VERIFY_POSTGRES_URL must point to a disposable PostgreSQL server; "
            "verification only creates isolated temporary schemas"
        )
    return value


def psycopg_url(value: str) -> str:
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


def migration_gate(value: str) -> None:
    suffix = secrets.token_hex(6)
    schemas = [f"verify_empty_{suffix}", f"verify_upgrade_{suffix}"]
    with (
        psycopg.connect(psycopg_url(value), autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        for schema in schemas:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
    try:
        base_env = {
            **os.environ,
            "APP_ENV": "test",
            "DEMO_MODE": "false",
            "ENABLE_FAKE_PUBLISHING": "false",
            "BILLING_PROVIDER": "disabled",
            "PAYMENT_PROVIDER": "cod",
            "APP_SECRET_KEY": "verification-only-secret-with-32-characters",
        }
        empty_env = {
            **base_env,
            "DATABASE_URL": value,
            "ALEMBIC_MIGRATION_SCHEMA": schemas[0],
        }
        run([sys.executable, "-m", "alembic", "upgrade", "head"], env=empty_env)
        current_env = {
            **base_env,
            "DATABASE_URL": value,
            "ALEMBIC_MIGRATION_SCHEMA": schemas[1],
        }
        run(
            [sys.executable, "-m", "alembic", "upgrade", "20260728_0024"],
            env=current_env,
        )
        run([sys.executable, "-m", "alembic", "upgrade", "head"], env=current_env)
    finally:
        with (
            psycopg.connect(psycopg_url(value), autocommit=True) as connection,
            connection.cursor() as cursor,
        ):
            for schema in schemas:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def remote_migration_gate(endpoint: str, secret_file: Path) -> None:
    secret = secret_file.read_text(encoding="utf-8").strip()
    if len(secret) < 32:
        raise RuntimeError("The release credential is missing or too short")
    request = urllib.request.Request(
        endpoint,
        method="POST",
        headers={"Authorization": f"Bearer {secret}"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        body = response.read().decode("utf-8")
    if response.status != 200 or '"status":"verified"' not in body.replace(" ", ""):
        raise RuntimeError("Remote PostgreSQL migration verification failed")
    print("Remote PostgreSQL migration gates passed", flush=True)


def fresh_frontend_gate() -> None:
    node_modules = (WEB / "node_modules").resolve()
    if node_modules.parent != WEB.resolve():
        raise RuntimeError("Refusing to remove a dependency directory outside web/")
    if node_modules.exists():
        shutil.rmtree(node_modules)
    npm = npm_command()
    node_env = {
        **os.environ,
        "PATH": f"{Path(npm).parent}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    run([npm, "ci"], cwd=WEB, env=node_env)
    run([npm, "run", "lint"], cwd=WEB, env=node_env)
    run([npm, "test"], cwd=WEB, env=node_env)
    run([npm, "run", "build"], cwd=WEB, env=node_env)
    shutil.rmtree(node_modules)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--postgres-url",
        help="Disposable PostgreSQL server URL; temporary schemas are created and removed",
    )
    parser.add_argument(
        "--migration-endpoint",
        help="Protected deployed /internal/release/verify-migrations endpoint",
    )
    parser.add_argument(
        "--release-secret-file",
        type=Path,
        help="Local file containing the release/cron Bearer credential",
    )
    parser.add_argument(
        "--deployment-url",
        help="Preview or Production URL to smoke-test after migration gates",
    )
    args = parser.parse_args()
    if args.postgres_url:
        os.environ["VERIFY_POSTGRES_URL"] = args.postgres_url

    tool_env = release_tool_env()
    run([sys.executable, "-m", "ruff", "check", "app", "tests", "scripts"], env=tool_env)
    run(
        [sys.executable, "-m", "ruff", "format", "--check", "app", "tests", "scripts"],
        env=tool_env,
    )
    run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--cache-dir",
            str(MYPY_CACHE),
            "app",
            "scripts",
        ],
        env=tool_env,
    )
    run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"], env=tool_env)
    run([sys.executable, "scripts/verify_git_integrity.py", "--require-release-sha"])
    run([sys.executable, "scripts/verify_provider_status.py"])
    run([sys.executable, "scripts/verify_environment_matrix.py"])
    run([sys.executable, "scripts/verify_env_example.py"])
    run([sys.executable, "scripts/verify_frontend_integration_wiring.py"])
    run([sys.executable, "scripts/verify_owner_actions.py"])
    run([sys.executable, "scripts/verify_production_access.py"])
    run([sys.executable, "scripts/verify_vercel_access_evidence.py"])
    run([sys.executable, "scripts/verify_operations_runbook.py"])
    run([sys.executable, "scripts/verify_repository_handoff_manifest.py"])
    run([sys.executable, "scripts/verify_deployment_evidence.py"])
    run([sys.executable, "scripts/verify_readiness_artifacts.py"])
    if args.migration_endpoint:
        if args.release_secret_file is None:
            raise RuntimeError("--release-secret-file is required with --migration-endpoint")
        remote_migration_gate(args.migration_endpoint, args.release_secret_file)
    else:
        migration_gate(postgres_url())
    fresh_frontend_gate()
    if args.deployment_url:
        run([sys.executable, "scripts/verify_deployment_smoke.py", args.deployment_url])
    run([sys.executable, "scripts/verify_release.py"])
    print("\nAll verification gates passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
