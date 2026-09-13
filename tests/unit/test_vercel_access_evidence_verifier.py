from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_readiness_artifacts import _load_json_object
from scripts.verify_vercel_access_evidence import validate_vercel_access_evidence

ROOT = Path(__file__).resolve().parents[2]
ACCESS_PATH = ROOT / "artifacts" / "production-readiness" / "vercel-access.md"
CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"
PROVIDER_STATUS_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"


def test_current_vercel_access_evidence_is_valid() -> None:
    assert (
        validate_vercel_access_evidence(
            ACCESS_PATH.read_text(encoding="utf-8"),
            _load_json_object(CURRENT_STATE_PATH),
            _load_json_object(PROVIDER_STATUS_PATH),
        )
        == []
    )


def test_vercel_access_evidence_rejects_stale_project_id() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    provider_status = _load_json_object(PROVIDER_STATUS_PATH)
    changed = deepcopy(current_state)
    changed["deployment"]["project_id"] = "prj_missing_from_vercel_access"

    findings = validate_vercel_access_evidence(
        ACCESS_PATH.read_text(encoding="utf-8"),
        changed,
        provider_status,
    )

    assert "vercel-access.md missing deployment.project_id from current-state" in findings


def test_vercel_access_evidence_rejects_token_assignment() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8") + "\nVERCEL_TOKEN=filled-in\n"

    findings = validate_vercel_access_evidence(
        markdown,
        _load_json_object(CURRENT_STATE_PATH),
        _load_json_object(PROVIDER_STATUS_PATH),
    )

    assert "vercel-access.md must not include an assignment for VERCEL_TOKEN" in findings


def test_vercel_access_evidence_rejects_ready_provider_status() -> None:
    current_state = _load_json_object(CURRENT_STATE_PATH)
    provider_status = _load_json_object(PROVIDER_STATUS_PATH)
    changed = deepcopy(provider_status)
    providers = changed["providers"]
    assert isinstance(providers, list)
    for provider in providers:
        if isinstance(provider, dict) and provider.get("provider") == "vercel":
            provider["status"] = "production_verified"

    findings = validate_vercel_access_evidence(
        ACCESS_PATH.read_text(encoding="utf-8"),
        current_state,
        changed,
    )

    assert "vercel provider status must remain blocked_missing_access" in findings


def test_vercel_access_evidence_requires_no_replacement_project_warning() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8").replace(
        "Do not create a replacement Vercel project",
        "Create a new project",
    )

    findings = validate_vercel_access_evidence(
        markdown,
        _load_json_object(CURRENT_STATE_PATH),
        _load_json_object(PROVIDER_STATUS_PATH),
    )

    assert (
        "vercel-access.md missing required phrase: Do not create a replacement Vercel project"
    ) in findings


def test_vercel_access_evidence_requires_current_connector_classification() -> None:
    markdown = ACCESS_PATH.read_text(encoding="utf-8").replace(
        "Project lookup returned `404 Not Found`",
        "Project lookup returned an old classification",
    )

    findings = validate_vercel_access_evidence(
        markdown,
        _load_json_object(CURRENT_STATE_PATH),
        _load_json_object(PROVIDER_STATUS_PATH),
    )

    assert (
        "vercel-access.md missing required phrase: Project lookup returned `404 Not Found`"
        in findings
    )
