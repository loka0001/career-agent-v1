"""Validate deployment IDs in release and operations evidence stay consistent."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEPLOYMENT_ID_PATTERN = re.compile(r"\bdpl_[A-Za-z0-9]+\b")
EVIDENCE_FILES = (
    Path("IMPLEMENTATION_STATUS.md"),
    Path("PRODUCTION_READINESS.md"),
    Path("FINAL_REPORT.md"),
    Path("artifacts/release/summary.md"),
    Path("artifacts/production-readiness/final-status.md"),
    Path("docs/OPERATIONS.md"),
    Path("docs/INCIDENT_RESPONSE.md"),
)


def _load_current_state(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("current-state.json must contain a JSON object")
    return value


def _expected_deployment_id(current_state: dict[str, Any]) -> str | None:
    deployment = current_state.get("deployment")
    if not isinstance(deployment, dict):
        return None
    value = deployment.get("latest_known_deployment_id")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def validate_deployment_evidence(root: Path = ROOT) -> list[str]:
    """Return findings for stale deployment IDs in operator/release evidence."""

    findings: list[str] = []
    current_state_path = root / "artifacts" / "agent" / "current-state.json"
    if not current_state_path.is_file():
        return ["missing current deployment evidence: artifacts/agent/current-state.json"]

    try:
        current_state = _load_current_state(current_state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"invalid current deployment evidence: {exc}"]

    expected = _expected_deployment_id(current_state)
    if expected is None:
        return ["current-state.json deployment.latest_known_deployment_id is missing"]
    if DEPLOYMENT_ID_PATTERN.fullmatch(expected) is None:
        findings.append(
            "current-state.json deployment.latest_known_deployment_id must look like dpl_*"
        )

    for relative in EVIDENCE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        deployment_ids = sorted(
            set(DEPLOYMENT_ID_PATTERN.findall(path.read_text(encoding="utf-8")))
        )
        stale = [deployment_id for deployment_id in deployment_ids if deployment_id != expected]
        if stale:
            findings.append(
                f"{relative.as_posix()} references stale deployment IDs: {', '.join(stale)}"
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing deployment evidence",
    )
    args = parser.parse_args()

    findings = validate_deployment_evidence(args.root)
    if findings:
        print("Deployment evidence verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Deployment evidence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
