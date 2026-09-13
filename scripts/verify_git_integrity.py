"""Verify that a release is tied to a clean, attributable Git checkout."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _git(args: list[str], *, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _release_sha_from_env() -> str:
    return os.getenv("RELEASE_SHA", "").strip() or os.getenv("GITHUB_SHA", "").strip()


def verify_git_integrity(
    *,
    cwd: Path = ROOT,
    require_clean: bool = True,
    require_remote: bool = True,
    require_release_sha: bool = False,
) -> list[str]:
    findings: list[str] = []
    try:
        inside = _git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ["not a Git worktree"]
    if inside != "true":
        findings.append("not a Git worktree")

    try:
        head = _git(["rev-parse", "--verify", "HEAD"], cwd=cwd)
    except subprocess.CalledProcessError:
        findings.append("HEAD commit is not available")
        head = ""
    if head and SHA_RE.fullmatch(head) is None:
        findings.append("HEAD commit is not a full 40-character SHA")

    if require_clean:
        status = _git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=cwd)
        if status:
            findings.append("working tree is not clean")

    if require_remote:
        remotes = _git(["remote"], cwd=cwd)
        if not remotes:
            findings.append("no Git remote is configured")

    release_sha = _release_sha_from_env()
    if require_release_sha and not release_sha:
        findings.append("RELEASE_SHA or GITHUB_SHA is required")
    if release_sha:
        if SHA_RE.fullmatch(release_sha) is None:
            findings.append("release SHA is not a full 40-character SHA")
        elif head and release_sha != head:
            findings.append("release SHA does not match HEAD")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, default=ROOT)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-missing-remote", action="store_true")
    parser.add_argument("--require-release-sha", action="store_true")
    args = parser.parse_args()

    findings = verify_git_integrity(
        cwd=args.cwd,
        require_clean=not args.allow_dirty,
        require_remote=not args.allow_missing_remote,
        require_release_sha=args.require_release_sha,
    )
    if findings:
        print("Git integrity verification failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Git integrity verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
