"""Validate production-readiness evidence artifacts for required structure and honesty."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.verify_deployment_evidence import validate_deployment_evidence
from scripts.verify_env_example import validate_env_example
from scripts.verify_environment_matrix import validate_environment_matrix
from scripts.verify_frontend_integration_wiring import validate_frontend_integration_wiring
from scripts.verify_operations_runbook import validate_operations_runbook
from scripts.verify_owner_actions import validate_owner_actions
from scripts.verify_production_access import validate_production_access
from scripts.verify_provider_status import load_json, validate_provider_status
from scripts.verify_repository_handoff_manifest import validate_manifest
from scripts.verify_vercel_access_evidence import validate_vercel_access_evidence

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ARTIFACTS = (
    Path("artifacts/agent/current-state.json"),
    Path("artifacts/agent/provider-status.json"),
    Path("artifacts/evidence/README.md"),
    Path("docs/OPERATIONS.md"),
    Path("docs/PROVIDER_ACTIVATION.md"),
    Path("docs/BACKUP_AND_RESTORE.md"),
    Path("docs/INCIDENT_RESPONSE.md"),
    Path("docs/PRODUCTION_ACCESS.md"),
    Path("docs/RELEASE_PROCESS.md"),
    Path("artifacts/production-readiness/final-status.md"),
    Path("artifacts/production-readiness/environment-matrix.md"),
    Path("artifacts/production-readiness/owner-actions.md"),
    Path("artifacts/production-readiness/vercel-access.md"),
    Path("artifacts/production-readiness/repository-handoff-manifest.json"),
)
REQUIRED_GIT_ADDABLE_ARTIFACTS = (
    Path("artifacts/agent/current-state.json"),
    Path("artifacts/agent/provider-status.json"),
    Path("artifacts/evidence/README.md"),
    Path("artifacts/production-readiness/environment-matrix.md"),
    Path("artifacts/production-readiness/final-status.md"),
    Path("artifacts/production-readiness/owner-actions.md"),
    Path("artifacts/production-readiness/vercel-access.md"),
    Path("artifacts/production-readiness/repository-handoff-manifest.json"),
    Path("artifacts/release/summary.md"),
)
REQUIRED_CURRENT_STATE_FIELDS = {
    "updated_at",
    "repository",
    "frontend_architecture",
    "backend_architecture",
    "database_provider",
    "auth_provider",
    "storage_provider",
    "queue_and_worker_architecture",
    "deployment",
    "provider_statuses",
    "completed_work",
    "unresolved_blockers",
    "tests_last_run",
    "next_executable_tasks",
}
ALLOWED_VERDICTS = {
    "Production ready",
    "Production ready with explicitly listed non-blocking limitations",
    "Not production ready",
}
REQUIRED_GITIGNORE_EXCEPTIONS = {
    f"!{path.as_posix()}" for path in REQUIRED_GIT_ADDABLE_ARTIFACTS
} | {
    "!artifacts/agent/",
    "!artifacts/evidence/",
    "!artifacts/production-readiness/",
    "!artifacts/release/",
}


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _missing_or_empty_required_artifacts(root: Path) -> list[str]:
    findings: list[str] = []
    for relative in REQUIRED_ARTIFACTS:
        path = root / relative
        if not path.is_file():
            findings.append(f"missing required artifact: {relative.as_posix()}")
            continue
        if path.stat().st_size == 0:
            findings.append(f"empty required artifact: {relative.as_posix()}")
    return findings


def _validate_required_artifact_gitignore_exceptions(root: Path) -> list[str]:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.is_file():
        return [".gitignore is required so repository import preserves evidence policy"]

    lines = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = sorted(REQUIRED_GITIGNORE_EXCEPTIONS - lines)
    if missing:
        return [".gitignore must unignore required readiness artifacts: " + ", ".join(missing)]
    return []


def _extract_honest_verdict(final_status: str) -> str | None:
    lines = final_status.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() != "## honest launch verdict":
            continue
        for candidate in lines[index + 1 :]:
            normalized = candidate.strip().strip("`").rstrip(".")
            if not normalized:
                continue
            if normalized in ALLOWED_VERDICTS:
                return normalized
            return None
    return None


def _extract_section_first_value(markdown: str, heading: str) -> str | None:
    lines = markdown.splitlines()
    normalized_heading = heading.strip().lower()
    for index, line in enumerate(lines):
        if line.strip().lower() != normalized_heading:
            continue
        collected: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                if collected:
                    break
                continue
            if stripped.startswith("#"):
                break
            collected.append(stripped.strip("`"))
        if collected:
            return " ".join(collected).rstrip(".")
        return None
    return None


def validate_readiness_artifacts(root: Path = ROOT) -> list[str]:
    """Return readiness artifact findings without expanding the launch claim."""

    findings = _missing_or_empty_required_artifacts(root)
    findings.extend(validate_frontend_integration_wiring(root))
    findings.extend(_validate_required_artifact_gitignore_exceptions(root))
    current_state_path = root / "artifacts" / "agent" / "current-state.json"
    provider_status_path = root / "artifacts" / "agent" / "provider-status.json"
    final_status_path = root / "artifacts" / "production-readiness" / "final-status.md"
    environment_matrix_path = root / "artifacts" / "production-readiness" / "environment-matrix.md"
    env_example_path = root / ".env.example"
    owner_actions_path = root / "artifacts" / "production-readiness" / "owner-actions.md"
    vercel_access_path = root / "artifacts" / "production-readiness" / "vercel-access.md"
    repository_handoff_manifest_path = (
        root / "artifacts" / "production-readiness" / "repository-handoff-manifest.json"
    )
    production_readiness_path = root / "PRODUCTION_READINESS.md"
    production_access_path = root / "docs" / "PRODUCTION_ACCESS.md"
    operations_path = root / "docs" / "OPERATIONS.md"
    incident_response_path = root / "docs" / "INCIDENT_RESPONSE.md"
    backup_restore_path = root / "docs" / "BACKUP_AND_RESTORE.md"
    provider_document: dict[str, Any] | None = None
    current_state: dict[str, Any] | None = None

    if current_state_path.is_file():
        try:
            current_state = _load_json_object(current_state_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(f"invalid current-state.json: {exc}")
        else:
            missing_fields = REQUIRED_CURRENT_STATE_FIELDS - set(current_state)
            if missing_fields:
                findings.append(
                    "current-state.json missing required fields: "
                    + ", ".join(sorted(missing_fields))
                )
            for list_field in ("completed_work", "unresolved_blockers", "tests_last_run"):
                if not isinstance(current_state.get(list_field), list):
                    findings.append(f"current-state.json {list_field} must be a list")
            repository = current_state.get("repository")
            if not isinstance(repository, dict):
                findings.append("current-state.json repository must be an object")
            elif repository.get("git_state") == "not_a_git_repository":
                blocker = str(repository.get("blocker", ""))
                if "no .git" not in blocker and "not a Git" not in blocker:
                    findings.append(
                        "current-state.json repository blocker must explain missing Git metadata"
                    )

            blockers = current_state.get("unresolved_blockers")
            if isinstance(blockers, list) and blockers:
                if not final_status_path.is_file():
                    findings.append("final-status.md is required when unresolved blockers exist")
                else:
                    final_status = final_status_path.read_text(encoding="utf-8")
                    verdict = _extract_honest_verdict(final_status)
                    if verdict != "Not production ready":
                        findings.append(
                            "final-status.md must use verdict 'Not production ready' while "
                            "current-state.json has unresolved blockers"
                        )
                if production_readiness_path.is_file():
                    production_readiness = production_readiness_path.read_text(encoding="utf-8")
                    verdict = _extract_section_first_value(
                        production_readiness,
                        "## Current Verdict",
                    )
                    if verdict is None:
                        findings.append(
                            "PRODUCTION_READINESS.md must contain a Current Verdict section"
                        )
                    elif not verdict.startswith("Not production ready"):
                        findings.append(
                            "PRODUCTION_READINESS.md Current Verdict must start with "
                            "'Not production ready' while current-state.json has "
                            "unresolved blockers"
                        )

    if provider_status_path.is_file():
        try:
            provider_document = load_json(provider_status_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(f"invalid provider-status.json: {exc}")
        else:
            findings.extend(validate_provider_status(provider_document))

    if environment_matrix_path.is_file() and provider_document is not None:
        environment_matrix = environment_matrix_path.read_text(encoding="utf-8")
        findings.extend(validate_environment_matrix(environment_matrix, provider_document))

    if env_example_path.is_file() and provider_document is not None:
        env_example = env_example_path.read_text(encoding="utf-8")
        findings.extend(validate_env_example(env_example, provider_document))

    if final_status_path.is_file():
        final_status = final_status_path.read_text(encoding="utf-8")
        verdict = _extract_honest_verdict(final_status)
        if verdict not in ALLOWED_VERDICTS:
            findings.append("final-status.md must contain exactly one allowed honest verdict")

    if owner_actions_path.is_file():
        findings.extend(
            validate_owner_actions(
                owner_actions_path.read_text(encoding="utf-8"),
                provider_document,
            )
        )

    if production_access_path.is_file() and current_state is not None:
        findings.extend(
            validate_production_access(
                production_access_path.read_text(encoding="utf-8"),
                current_state,
            )
        )

    if vercel_access_path.is_file() and current_state is not None and provider_document is not None:
        findings.extend(
            validate_vercel_access_evidence(
                vercel_access_path.read_text(encoding="utf-8"),
                current_state,
                provider_document,
            )
        )

    if repository_handoff_manifest_path.is_file():
        try:
            repository_handoff_manifest = _load_json_object(repository_handoff_manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(f"invalid repository-handoff-manifest.json: {exc}")
        else:
            findings.extend(validate_manifest(repository_handoff_manifest, root))

    if (
        operations_path.is_file()
        and incident_response_path.is_file()
        and backup_restore_path.is_file()
        and current_state is not None
    ):
        findings.extend(
            validate_operations_runbook(
                {
                    "OPERATIONS.md": operations_path.read_text(encoding="utf-8"),
                    "INCIDENT_RESPONSE.md": incident_response_path.read_text(encoding="utf-8"),
                    "BACKUP_AND_RESTORE.md": backup_restore_path.read_text(encoding="utf-8"),
                },
                current_state,
            )
        )

    findings.extend(validate_deployment_evidence(root))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing production-readiness artifacts",
    )
    args = parser.parse_args()

    findings = validate_readiness_artifacts(args.root)
    if findings:
        print("Readiness artifact verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Readiness artifact verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
