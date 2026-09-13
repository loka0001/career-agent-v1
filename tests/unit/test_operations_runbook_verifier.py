from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_operations_runbook import (
    BACKUP_REQUIRED_PHRASES,
    INCIDENT_REQUIRED_PHRASES,
    OPERATIONS_REQUIRED_PHRASES,
    validate_operations_runbook,
)
from scripts.verify_readiness_artifacts import _load_json_object

ROOT = Path(__file__).resolve().parents[2]
CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"
RUNBOOKS = {
    "OPERATIONS.md": ROOT / "docs" / "OPERATIONS.md",
    "INCIDENT_RESPONSE.md": ROOT / "docs" / "INCIDENT_RESPONSE.md",
    "BACKUP_AND_RESTORE.md": ROOT / "docs" / "BACKUP_AND_RESTORE.md",
}


def _current_documents() -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8") for name, path in RUNBOOKS.items()}


def test_current_operations_runbooks_are_valid() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)

    assert validate_operations_runbook(_current_documents(), current_state) == []


def test_operations_runbook_rejects_stale_deployment_id() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    changed = deepcopy(current_state)
    changed["deployment"]["latest_known_deployment_id"] = "dpl_missing_from_runbooks"

    findings = validate_operations_runbook(_current_documents(), changed)

    assert "OPERATIONS.md missing deployment.latest_known_deployment_id" in findings
    assert "INCIDENT_RESPONSE.md missing deployment.latest_known_deployment_id" in findings


def test_operations_runbook_rejects_secret_like_values() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    documents = _current_documents()
    documents["OPERATIONS.md"] += "\nsk-" + "opsrunbook1234567890abcdef\n"

    findings = validate_operations_runbook(documents, current_state)

    assert any("OPERATIONS.md contains a secret-looking OpenAI key" in item for item in findings)


def test_operations_runbook_rejects_missing_alert_rule() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    documents = _current_documents()
    phrase = "Worker or scheduler no successful drain for 15 minutes"
    assert phrase in OPERATIONS_REQUIRED_PHRASES
    documents["OPERATIONS.md"] = documents["OPERATIONS.md"].replace(phrase, "worker pending")

    assert (
        f"OPERATIONS.md missing required operations phrase: {phrase}"
        in validate_operations_runbook(documents, current_state)
    )


def test_operations_runbook_rejects_missing_incident_smoke_command() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    documents = _current_documents()
    phrase = "scripts/verify_deployment_smoke.py"
    assert phrase in INCIDENT_REQUIRED_PHRASES
    documents["INCIDENT_RESPONSE.md"] = documents["INCIDENT_RESPONSE.md"].replace(
        phrase,
        "manual smoke",
    )

    assert (
        f"INCIDENT_RESPONSE.md missing required operations phrase: {phrase}"
        in validate_operations_runbook(documents, current_state)
    )


def test_operations_runbook_rejects_missing_backup_restore_safety() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    documents = _current_documents()
    phrase = "separate non-production destination"
    assert phrase in BACKUP_REQUIRED_PHRASES
    documents["BACKUP_AND_RESTORE.md"] = documents["BACKUP_AND_RESTORE.md"].replace(
        phrase,
        "same database",
    )

    assert (
        f"BACKUP_AND_RESTORE.md missing required operations phrase: {phrase}"
        in validate_operations_runbook(documents, current_state)
    )
