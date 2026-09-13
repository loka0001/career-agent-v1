from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_deployment_evidence import validate_deployment_evidence

ROOT = Path(__file__).resolve().parents[2]


def test_current_deployment_evidence_is_consistent() -> None:
    assert validate_deployment_evidence(ROOT) == []


def test_deployment_evidence_rejects_stale_deployment_ids(tmp_path: Path) -> None:
    (tmp_path / "artifacts/agent").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "artifacts/agent/current-state.json").write_text(
        json.dumps(
            {"deployment": {"latest_known_deployment_id": "dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx"}}
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs/INCIDENT_RESPONSE.md").write_text(
        "vercel inspect dpl_ETZHLwxNdjQYjJXyX9ead2HAT6pi\n",
        encoding="utf-8",
    )

    assert validate_deployment_evidence(tmp_path) == [
        "docs/INCIDENT_RESPONSE.md references stale deployment IDs: "
        "dpl_ETZHLwxNdjQYjJXyX9ead2HAT6pi"
    ]
