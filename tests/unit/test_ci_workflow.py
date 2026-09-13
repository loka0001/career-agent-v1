from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _workflow() -> dict[str, Any]:
    path = ROOT / ".github" / "workflows" / "ci.yml"
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    assert isinstance(value, dict)
    return value


def _job_commands(job_name: str) -> list[str]:
    workflow = _workflow()
    job = workflow["jobs"][job_name]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    commands: list[str] = []
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("run"), str):
            commands.append(step["run"])
    return commands


def test_secret_scan_job_runs_provider_status_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_provider_status.py" in commands


def test_secret_scan_job_runs_environment_matrix_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_environment_matrix.py" in commands


def test_secret_scan_job_runs_env_example_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_env_example.py" in commands


def test_secret_scan_job_runs_readiness_artifact_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_readiness_artifacts.py" in commands


def test_secret_scan_job_runs_deployment_evidence_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_deployment_evidence.py" in commands


def test_secret_scan_job_runs_production_access_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_production_access.py" in commands


def test_secret_scan_job_runs_vercel_access_evidence_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_vercel_access_evidence.py" in commands


def test_secret_scan_job_runs_operations_runbook_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_operations_runbook.py" in commands


def test_secret_scan_job_runs_repository_handoff_manifest_verifier() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_repository_handoff_manifest.py" in commands


def test_secret_scan_job_keeps_git_and_release_integrity_gates() -> None:
    commands = _job_commands("secret-scan")

    assert "uv run python scripts/verify_git_integrity.py --require-release-sha" in commands
    assert "uv run python scripts/verify_release.py" in commands
