from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_production_access import validate_production_access
from scripts.verify_readiness_artifacts import _load_json_object

ROOT = Path(__file__).resolve().parents[2]
ACCESS_PATH = ROOT / "docs" / "PRODUCTION_ACCESS.md"
CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"


def test_current_production_access_doc_is_valid() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8")
    current_state = _load_json_object(CURRENT_STATE_PATH)

    assert validate_production_access(markdown, current_state) == []


def test_production_access_rejects_missing_current_project_id() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8")
    current_state = _load_json_object(CURRENT_STATE_PATH)
    changed = deepcopy(current_state)
    changed["deployment"]["project_id"] = "prj_missing_from_doc"

    findings = validate_production_access(markdown, changed)

    assert "PRODUCTION_ACCESS.md missing deployment.project_id from current-state" in findings


def test_production_access_rejects_secret_like_values() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8")
    current_state = _load_json_object(CURRENT_STATE_PATH)
    fake_secret = "sk-" + "prodaccess1234567890abcdef"

    findings = validate_production_access(f"{markdown}\n{fake_secret}\n", current_state)

    assert any("secret-looking OpenAI key" in finding for finding in findings)


def test_production_access_rejects_vercel_token_assignment() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8").replace(
        "`VERCEL_TOKEN`",
        "VERCEL_TOKEN=filled-in",
        1,
    )
    current_state = _load_json_object(CURRENT_STATE_PATH)

    assert (
        "PRODUCTION_ACCESS.md must not include an assignment for VERCEL_TOKEN"
        in validate_production_access(markdown, current_state)
    )


def test_production_access_rejects_missing_local_secret_marker() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8").replace(
        ".vercel/.cron-secret.local",
        ".vercel/.other-secret.local",
    )
    current_state = _load_json_object(CURRENT_STATE_PATH)

    assert (
        "PRODUCTION_ACCESS.md missing local secret marker: .vercel/.cron-secret.local"
        in validate_production_access(markdown, current_state)
    )
