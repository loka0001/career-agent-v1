from __future__ import annotations

from pathlib import Path

from scripts.verify_owner_actions import validate_owner_actions
from scripts.verify_provider_status import load_json

ROOT = Path(__file__).resolve().parents[2]
OWNER_ACTIONS_PATH = ROOT / "artifacts" / "production-readiness" / "owner-actions.md"
PROVIDER_STATUS_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"


def test_current_owner_actions_are_valid() -> None:
    content = OWNER_ACTIONS_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_STATUS_PATH)

    assert validate_owner_actions(content, provider_document) == []


def test_owner_actions_reject_missing_exact_field() -> None:
    content = OWNER_ACTIONS_PATH.read_text(encoding="utf-8")

    findings = validate_owner_actions(content.replace("| Exact page |", "| Page |", 1))

    assert "## Current Sequential Blocker missing field: Exact page" in findings


def test_owner_actions_reject_secret_like_values() -> None:
    content = OWNER_ACTIONS_PATH.read_text(encoding="utf-8")
    fake_secret = "sk-" + "owneraction1234567890abcdef"

    findings = validate_owner_actions(content + f"\n{fake_secret}\n")

    assert any("secret-looking OpenAI key" in finding for finding in findings)


def test_owner_actions_reject_missing_provider_required_key_name() -> None:
    content = OWNER_ACTIONS_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_STATUS_PATH)
    content_without_key = content.replace("EXPECTED_MIGRATION_HEAD", "MIGRATION_MARKER", 1)

    findings = validate_owner_actions(content_without_key, provider_document)

    assert (
        "owner-actions.md missing provider-required key names: EXPECTED_MIGRATION_HEAD" in findings
    )
