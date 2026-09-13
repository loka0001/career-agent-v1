"""Validate production operations runbooks stay executable and redacted."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.verify_provider_status import SECRET_PATTERNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"

RUNBOOK_PATHS = {
    "OPERATIONS.md": ROOT / "docs" / "OPERATIONS.md",
    "INCIDENT_RESPONSE.md": ROOT / "docs" / "INCIDENT_RESPONSE.md",
    "BACKUP_AND_RESTORE.md": ROOT / "docs" / "BACKUP_AND_RESTORE.md",
}

OPERATIONS_REQUIRED_PHRASES = {
    "/health/live",
    "/health/ready",
    "scripts/verify_deployment_smoke.py",
    "scripts.worker",
    "ENABLE_BACKGROUND_WORKER",
    "SERVERLESS_MODE",
    "/api/v1/operator/alerts",
    "vercel logs",
    "No passwords, bearer tokens, cookies, authorization headers",
    "Queue `failed > 0`",
    "Queue `oldest_job_age_seconds > 900`",
    "Worker or scheduler no successful drain for 15 minutes",
    "Database backup or restore drill failure",
    "worker_runtime_missing",
    "production_readiness_incomplete",
}

INCIDENT_REQUIRED_PHRASES = {
    "/health/live",
    "/health/ready",
    "vercel inspect",
    "vercel logs",
    "scripts/verify_deployment_smoke.py",
    "Freeze non-essential deployments",
    "Do not delete production data during triage",
    "Do not include raw secrets, customer messages, cookies, bearer tokens, or payment data",
}

BACKUP_REQUIRED_PHRASES = {
    "VERIFY_POSTGRES_URL",
    "scripts/verify_backup_restore.py",
    "pg_dump",
    "pg_restore",
    "alembic_version",
    "Never restore over the active production database",
    "separate non-production destination",
    "tenant isolation",
    "migration head matching production",
}


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _deployment_values(current_state: dict[str, Any]) -> dict[str, str]:
    deployment = current_state.get("deployment")
    if not isinstance(deployment, dict):
        return {}
    keys = (
        "production_url",
        "project_name",
        "team_slug_latest_known",
        "latest_known_deployment_id",
    )
    values: dict[str, str] = {}
    for key in keys:
        value = deployment.get(key)
        if isinstance(value, str) and value.strip():
            values[key] = value.strip()
    return values


def _scan_secret_strings(documents: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for document_name, markdown in documents.items():
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(markdown):
                findings.append(f"{document_name} contains a secret-looking {label}")
    return findings


def _require_phrases(document_name: str, markdown: str, phrases: set[str]) -> list[str]:
    return [
        f"{document_name} missing required operations phrase: {phrase}"
        for phrase in sorted(phrases)
        if phrase not in markdown
    ]


def validate_operations_runbook(
    documents: dict[str, str],
    current_state: dict[str, Any],
) -> list[str]:
    """Return runbook findings without exposing sensitive values."""

    findings = _scan_secret_strings(documents)
    deployment_values = _deployment_values(current_state)
    operations = documents.get("OPERATIONS.md", "")
    incident = documents.get("INCIDENT_RESPONSE.md", "")
    backup = documents.get("BACKUP_AND_RESTORE.md", "")

    for key, value in deployment_values.items():
        if key == "production_url":
            if value not in operations:
                findings.append("OPERATIONS.md missing deployment.production_url")
            if value not in incident:
                findings.append("INCIDENT_RESPONSE.md missing deployment.production_url")
        elif key == "latest_known_deployment_id":
            if value not in operations:
                findings.append("OPERATIONS.md missing deployment.latest_known_deployment_id")
            if value not in incident:
                findings.append(
                    "INCIDENT_RESPONSE.md missing deployment.latest_known_deployment_id"
                )
        elif value not in operations:
            findings.append(f"OPERATIONS.md missing deployment.{key}")

    findings.extend(_require_phrases("OPERATIONS.md", operations, OPERATIONS_REQUIRED_PHRASES))
    findings.extend(_require_phrases("INCIDENT_RESPONSE.md", incident, INCIDENT_REQUIRED_PHRASES))
    findings.extend(_require_phrases("BACKUP_AND_RESTORE.md", backup, BACKUP_REQUIRED_PHRASES))

    if (
        "restore over the active production database" in backup
        and "separate non-production destination" not in backup
    ):
        findings.append(
            "BACKUP_AND_RESTORE.md must pair restore warnings with a separate "
            "non-production destination"
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-state", type=Path, default=DEFAULT_CURRENT_STATE_PATH)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing docs and production-readiness artifacts",
    )
    args = parser.parse_args()

    runbook_paths = {
        name: args.root / path.relative_to(ROOT) for name, path in RUNBOOK_PATHS.items()
    }

    try:
        current_state = _load_json_object(args.current_state)
        documents = {name: path.read_text(encoding="utf-8") for name, path in runbook_paths.items()}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Operations runbook verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_operations_runbook(documents, current_state)
    if findings:
        print("Operations runbook verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Operations runbook verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
