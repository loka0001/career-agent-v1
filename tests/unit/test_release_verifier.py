from __future__ import annotations

from pathlib import Path

import pytest

import scripts.verify_release as verify_release


def test_release_verifier_rejects_generated_tool_cache_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for cache_dir in (".mypy_cache", ".pytest_cache", ".ruff_cache"):
        (tmp_path / cache_dir).mkdir()
    monkeypatch.setattr(verify_release, "ROOT", tmp_path)

    assert verify_release.main() == 1
