"""Validate production access documentation stays safe and aligned."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.verify_provider_status import SECRET_PATTERNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCESS_PATH = ROOT / "docs" / "PRODUCTION_ACCESS.md"
DEFAULT_CURRENT_STATE_PATH = ROOT / "artifacts" / "agent" / "current-state.json"

REQUIRED_LOCAL_SECRET_MARKERS = {
    ".vercel/.cron-secret.local",
    ".vercel/.env.production.migrate.local",
    ".env*",
    "commerce-production-merchant-password.dpapi",
}
REQUIRED_SAFETY_PHRASES = {
    "Use least privilege",
    "require MFA",
    "Do not print the plaintext password",
    "These files must never be committed",
}
REQUIRED_DEPLOYMENT_CONTROL_KEYS = {
    "VERCEL_TOKEN",
    "VERCEL_ORG_ID",
    "VERCEL_PROJECT_ID",
}


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _expected_deployment_values(current_state: dict[str, Any]) -> dict[str, str]:
    deployment = current_state.get("deployment")
    if not isinstance(deployment, dict):
        return {}
    keys = (
        "project_name",
        "project_id",
        "org_id",
        "team_slug_latest_known",
    )
    values: dict[str, str] = {}
    for key in keys:
        value = deployment.get(key)
        if isinstance(value, str) and value.strip():
            values[key] = value.strip()
    return values


def validate_production_access(
    markdown: str,
    current_state: dict[str, Any],
) -> list[str]:
    """Return production access documentation findings without exposing values."""

    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(markdown):
            findings.append(f"PRODUCTION_ACCESS.md contains a secret-looking {label}")

    expected_values = _expected_deployment_values(current_state)
    for key, value in expected_values.items():
        if value not in markdown:
            findings.append(f"PRODUCTION_ACCESS.md missing deployment.{key} from current-state")

    for marker in REQUIRED_LOCAL_SECRET_MARKERS:
        if marker not in markdown:
            findings.append(f"PRODUCTION_ACCESS.md missing local secret marker: {marker}")

    for phrase in REQUIRED_SAFETY_PHRASES:
        if phrase not in markdown:
            findings.append(f"PRODUCTION_ACCESS.md missing safety phrase: {phrase}")

    for key in REQUIRED_DEPLOYMENT_CONTROL_KEYS:
        if key not in markdown:
            findings.append(f"PRODUCTION_ACCESS.md missing deployment control key name: {key}")
        if f"{key}=" in markdown:
            findings.append(f"PRODUCTION_ACCESS.md must not include an assignment for {key}")

    if "names only" not in markdown.lower() and "secret values" not in markdown.lower():
        findings.append("PRODUCTION_ACCESS.md must state that deployment values are names only")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_ACCESS_PATH)
    parser.add_argument("--current-state", type=Path, default=DEFAULT_CURRENT_STATE_PATH)
    args = parser.parse_args()

    try:
        markdown = args.path.read_text(encoding="utf-8")
        current_state = _load_json_object(args.current_state)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Production access verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_production_access(markdown, current_state)
    if findings:
        print("Production access verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Production access verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
