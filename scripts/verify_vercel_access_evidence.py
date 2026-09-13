"""Validate Vercel access evidence is precise, current, and redacted."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.verify_provider_status import SECRET_PATTERNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCESS_PATH = ROOT / "artifacts" / "production-readiness" / "vercel-access.md"
DEFAULT_CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"
DEFAULT_PROVIDER_STATUS_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"

REQUIRED_PHRASES = {
    "_list_teams",
    "_list_projects",
    "_get_project",
    "_get_deployment",
    "team visible",
    "not the production project",
    "Project lookup returned `404 Not Found`",
    "Deployment lookup returned `404 Not Found`",
    "Public URL is reachable but fails the current deployment smoke contract",
    "blocked_missing_access",
    "Do not create a replacement Vercel project",
    "Preview deployment cannot be created",
    "scripts/verify_deployment_smoke.py <preview-url>",
    "VERCEL_TOKEN",
    "VERCEL_ORG_ID",
    "VERCEL_PROJECT_ID",
    "names only",
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
        "project_id",
        "org_id",
        "team_slug_latest_known",
        "latest_known_deployment_id",
    )
    values: dict[str, str] = {}
    for key in keys:
        value = deployment.get(key)
        if isinstance(value, str) and value.strip():
            values[key] = value.strip()
    return values


def _vercel_provider(provider_status: dict[str, Any]) -> dict[str, Any] | None:
    providers = provider_status.get("providers")
    if not isinstance(providers, list):
        return None
    for provider in providers:
        if isinstance(provider, dict) and provider.get("provider") == "vercel":
            return provider
    return None


def validate_vercel_access_evidence(
    markdown: str,
    current_state: dict[str, Any],
    provider_status: dict[str, Any],
) -> list[str]:
    """Return findings for Vercel access evidence without exposing values."""

    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(markdown):
            findings.append(f"vercel-access.md contains a secret-looking {label}")

    for key, value in _deployment_values(current_state).items():
        if value not in markdown:
            findings.append(f"vercel-access.md missing deployment.{key} from current-state")

    for phrase in REQUIRED_PHRASES:
        if phrase not in markdown:
            findings.append(f"vercel-access.md missing required phrase: {phrase}")

    for key in ("VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"):
        if f"{key}=" in markdown:
            findings.append(f"vercel-access.md must not include an assignment for {key}")

    provider = _vercel_provider(provider_status)
    if provider is None:
        findings.append("provider-status.json missing vercel provider record")
    elif provider.get("status") != "blocked_missing_access":
        findings.append("vercel provider status must remain blocked_missing_access")

    deployment_control = current_state.get("deployment")
    if not isinstance(deployment_control, dict):
        findings.append("current-state deployment must be an object")
    elif deployment_control.get("deployment_control") != "blocked_missing_vercel_project_access":
        findings.append(
            "current-state deployment_control must record blocked_missing_vercel_project_access"
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_ACCESS_PATH)
    parser.add_argument("--current-state", type=Path, default=DEFAULT_CURRENT_STATE_PATH)
    parser.add_argument("--provider-status", type=Path, default=DEFAULT_PROVIDER_STATUS_PATH)
    args = parser.parse_args()

    try:
        markdown = args.path.read_text(encoding="utf-8")
        current_state = _load_json_object(args.current_state)
        provider_status = _load_json_object(args.provider_status)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Vercel access evidence verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_vercel_access_evidence(markdown, current_state, provider_status)
    if findings:
        print("Vercel access evidence verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Vercel access evidence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
