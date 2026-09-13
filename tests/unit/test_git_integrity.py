from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.verify_git_integrity import verify_git_integrity

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci@example.invalid")
    _git(repo, "config", "user.name", "CI")
    (repo / "README.md").write_text("release fixture\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "remote", "add", "origin", "https://example.invalid/repo.git")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_git_integrity_accepts_clean_repo_with_matching_release_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _repo(tmp_path)
    monkeypatch.setenv("RELEASE_SHA", head)

    assert verify_git_integrity(cwd=repo, require_release_sha=True) == []


def test_git_integrity_rejects_dirty_tree(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "README.md").write_text("changed\n", encoding="utf-8")

    assert "working tree is not clean" in verify_git_integrity(cwd=repo)


def test_git_integrity_rejects_missing_remote(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    _git(repo, "remote", "remove", "origin")

    assert "no Git remote is configured" in verify_git_integrity(cwd=repo)


def test_git_integrity_rejects_release_sha_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _ = _repo(tmp_path)
    monkeypatch.setenv("RELEASE_SHA", "0" * 40)

    assert "release SHA does not match HEAD" in verify_git_integrity(
        cwd=repo,
        require_release_sha=True,
    )


def test_git_integrity_reports_non_git_directory(tmp_path: Path) -> None:
    assert verify_git_integrity(cwd=tmp_path) == ["not a Git worktree"]
