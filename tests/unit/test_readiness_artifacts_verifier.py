from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_environment_matrix import CRITICAL_RUNTIME_KEYS
from scripts.verify_operations_runbook import (
    BACKUP_REQUIRED_PHRASES,
    INCIDENT_REQUIRED_PHRASES,
    OPERATIONS_REQUIRED_PHRASES,
)
from scripts.verify_provider_status import ALLOWED_STATUSES, REQUIRED_PROVIDERS
from scripts.verify_readiness_artifacts import validate_readiness_artifacts
from scripts.verify_repository_handoff_manifest import build_manifest
from scripts.verify_vercel_access_evidence import REQUIRED_PHRASES as VERCEL_REQUIRED_PHRASES

ROOT = Path(__file__).resolve().parents[2]


def test_current_readiness_artifacts_are_valid() -> None:
    assert validate_readiness_artifacts(ROOT) == []


def _write_minimal_artifacts(
    root: Path,
    *,
    verdict: str = "Not production ready.",
    production_readiness_verdict: str = "Not production ready - local test blockers remain.",
) -> None:
    for relative in (
        "artifacts/agent",
        "artifacts/evidence",
        "docs",
        "artifacts/production-readiness",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    current_state = {
        "updated_at": "2026-08-01T09:30:00+03:00",
        "repository": {
            "git_state": "not_a_git_repository",
            "blocker": "Local workspace has no .git directory.",
        },
        "frontend_architecture": {},
        "backend_architecture": {},
        "database_provider": {},
        "auth_provider": {},
        "storage_provider": {},
        "queue_and_worker_architecture": {},
        "deployment": {
            "production_url": "https://commerce.example.com",
            "project_name": "commerce-example",
            "project_id": "prj_example",
            "org_id": "team_example",
            "team_slug_latest_known": "example-team",
            "latest_known_deployment_id": "dpl_example",
            "deployment_control": "blocked_missing_vercel_project_access",
        },
        "provider_statuses": {},
        "completed_work": ["local gate"],
        "unresolved_blockers": ["Git metadata is unavailable."],
        "tests_last_run": [{"command": "unit", "result": "passed"}],
        "next_executable_tasks": ["Import into Git."],
    }
    (root / "artifacts/agent/current-state.json").write_text(
        json.dumps(current_state),
        encoding="utf-8",
    )
    provider_document = {
        "updated_at": "2026-08-01T09:30:00+03:00",
        "status_values": sorted(ALLOWED_STATUSES),
        "providers": [
            {
                "provider": provider,
                "status": "blocked_missing_access",
                "account_or_project_identifier": "not supplied",
                "required_environment_key_names": ["EXAMPLE_ENV_NAME"],
                "required_keys_present": "not_visible_in_local_runtime",
                "last_test": "local artifact test",
                "timestamp": "2026-08-01T09:30:00+03:00",
                "safe_external_event_or_request_id": None,
                "remaining_blocker": "external access unavailable",
                "exact_owner_action": "provide external access",
            }
            for provider in sorted(REQUIRED_PROVIDERS)
        ],
    }
    (root / "artifacts/agent/provider-status.json").write_text(
        json.dumps(provider_document),
        encoding="utf-8",
    )
    matrix_rows = [
        (
            key,
            "Required runtime key",
            "production",
            "not present in local runtime",
            "yes" if key.endswith(("KEY", "SECRET", "TOKEN", "URL")) else "no",
            "Test",
            "rotate on exposure" if key.endswith(("KEY", "SECRET", "TOKEN", "URL")) else "no",
            "artifact verifier",
        )
        for key in sorted(CRITICAL_RUNTIME_KEYS | {"EXAMPLE_ENV_NAME"})
    ]
    matrix_lines = [
        "# Environment Variable Matrix",
        "",
        "Generated: 2026-08-01",
        "",
        "Secret values are intentionally omitted.",
        "",
        "| Variable | Purpose | Required environments | Current presence | Secret | "
        "Provider | Rotation requirement | Validation method |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *["| " + " | ".join(row) + " |" for row in matrix_rows],
        "",
    ]
    (root / "artifacts/production-readiness/environment-matrix.md").write_text(
        "\n".join(matrix_lines),
        encoding="utf-8",
    )
    vercel_access_lines = [
        "https://commerce.example.com",
        "commerce-example",
        "prj_example",
        "team_example",
        "example-team",
        "dpl_example",
        *sorted(VERCEL_REQUIRED_PHRASES),
    ]
    (root / "artifacts/production-readiness/vercel-access.md").write_text(
        "\n".join(vercel_access_lines) + "\n",
        encoding="utf-8",
    )
    for relative in (
        "artifacts/evidence/README.md",
        "docs/PROVIDER_ACTIVATION.md",
        "docs/PRODUCTION_ACCESS.md",
        "docs/RELEASE_PROCESS.md",
    ):
        (root / relative).write_text("present\n", encoding="utf-8")
    (root / "docs/OPERATIONS.md").write_text(
        "\n".join(sorted(OPERATIONS_REQUIRED_PHRASES)) + "\n",
        encoding="utf-8",
    )
    (root / "docs/INCIDENT_RESPONSE.md").write_text(
        "\n".join(sorted(INCIDENT_REQUIRED_PHRASES)) + "\n",
        encoding="utf-8",
    )
    (root / "docs/BACKUP_AND_RESTORE.md").write_text(
        "\n".join(sorted(BACKUP_REQUIRED_PHRASES)) + "\n",
        encoding="utf-8",
    )
    (root / "artifacts/production-readiness/final-status.md").write_text(
        f"## Honest Launch Verdict\n\n{verdict}\n",
        encoding="utf-8",
    )
    (root / "PRODUCTION_READINESS.md").write_text(
        f"## Current Verdict\n\n`{production_readiness_verdict}`\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(
        "\n".join(
            [
                "artifacts/*",
                "!artifacts/agent/",
                "artifacts/agent/*",
                "!artifacts/agent/current-state.json",
                "!artifacts/agent/provider-status.json",
                "!artifacts/evidence/",
                "artifacts/evidence/*",
                "!artifacts/evidence/README.md",
                "!artifacts/production-readiness/",
                "artifacts/production-readiness/*",
                "!artifacts/production-readiness/environment-matrix.md",
                "!artifacts/production-readiness/final-status.md",
                "!artifacts/production-readiness/owner-actions.md",
                "!artifacts/production-readiness/vercel-access.md",
                "!artifacts/production-readiness/repository-handoff-manifest.json",
                "!artifacts/release/",
                "artifacts/release/*",
                "!artifacts/release/summary.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = build_manifest(root, generated_at="2026-08-01T10:55:00+00:00")
    (root / "artifacts/production-readiness/repository-handoff-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_readiness_artifacts_reject_missing_required_artifact(tmp_path: Path) -> None:
    _write_minimal_artifacts(tmp_path)
    (tmp_path / "docs/OPERATIONS.md").unlink()

    assert "missing required artifact: docs/OPERATIONS.md" in validate_readiness_artifacts(tmp_path)


def test_readiness_artifacts_reject_ready_verdict_with_blockers(tmp_path: Path) -> None:
    _write_minimal_artifacts(tmp_path, verdict="Production ready.")

    assert (
        "final-status.md must use verdict 'Not production ready' while "
        "current-state.json has unresolved blockers"
    ) in validate_readiness_artifacts(tmp_path)


def test_readiness_artifacts_reject_top_level_ready_claim_with_blockers(
    tmp_path: Path,
) -> None:
    _write_minimal_artifacts(
        tmp_path,
        production_readiness_verdict="DEPLOYED - CORE RELEASE VERIFIED",
    )

    assert (
        "PRODUCTION_READINESS.md Current Verdict must start with 'Not production ready' "
        "while current-state.json has unresolved blockers"
    ) in validate_readiness_artifacts(tmp_path)


def test_readiness_artifacts_reject_ignored_required_evidence(
    tmp_path: Path,
) -> None:
    _write_minimal_artifacts(tmp_path)
    (tmp_path / ".gitignore").write_text("artifacts/\n", encoding="utf-8")

    assert (
        ".gitignore must unignore required readiness artifacts: "
        "!artifacts/agent/, !artifacts/agent/current-state.json, "
        "!artifacts/agent/provider-status.json, !artifacts/evidence/, "
        "!artifacts/evidence/README.md, !artifacts/production-readiness/, "
        "!artifacts/production-readiness/environment-matrix.md, "
        "!artifacts/production-readiness/final-status.md, "
        "!artifacts/production-readiness/owner-actions.md, "
        "!artifacts/production-readiness/repository-handoff-manifest.json, "
        "!artifacts/production-readiness/vercel-access.md, !artifacts/release/, "
        "!artifacts/release/summary.md"
    ) in validate_readiness_artifacts(tmp_path)
