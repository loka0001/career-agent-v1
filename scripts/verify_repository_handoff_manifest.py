"""Create and verify a deterministic repository handoff manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.verify_provider_status import SECRET_PATTERNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = (
    ROOT / "artifacts" / "production-readiness" / ("repository-handoff-manifest.json")
)

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    ".vercel",
    ".vercel_python_packages",
    "__pycache__",
    "_uv",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "playwright-report",
    "screenshots",
    "test-results",
}
EXCLUDED_TOP_LEVEL_DIRS = {
    "media",
    "public",
}
EXCLUDED_SUFFIXES = {
    ".7z",
    ".db",
    ".gz",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".zip",
}
EXCLUDED_NAME_PREFIXES = {
    ".env",
}
ALLOWED_ARTIFACT_FILES = {
    "artifacts/evidence/README.md",
    "artifacts/production-readiness/environment-matrix.md",
    "artifacts/production-readiness/final-status.md",
    "artifacts/production-readiness/owner-actions.md",
    "artifacts/production-readiness/vercel-access.md",
    "artifacts/release/summary.md",
}
SELF_PATH = "artifacts/production-readiness/repository-handoff-manifest.json"


def _relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded_path(relative: str) -> bool:
    path = Path(relative)
    parts = path.parts
    if not parts:
        return True
    if parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
        return True
    if parts[0] == "data" and not relative.startswith("data/seeds/"):
        return True
    if any(part in EXCLUDED_DIR_NAMES or part.startswith(".venv-") for part in parts):
        return True
    if path.name == ".coverage":
        return True
    if relative == ".env.example":
        return False
    if path.name.startswith(tuple(EXCLUDED_NAME_PREFIXES)):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if "credentials" in path.stem.lower() and path.suffix.lower() in {".csv", ".json"}:
        return True
    if relative == SELF_PATH:
        return True
    if relative.startswith("artifacts/"):
        return relative not in ALLOWED_ARTIFACT_FILES
    return False


def _iter_handoff_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = _relative_path(path, root)
        if _is_excluded_path(relative):
            continue
        files.append(path)
    return sorted(files, key=lambda item: _relative_path(item, root))


def _canonical_file_bytes(path: Path) -> bytes:
    """Return platform-stable bytes for text and exact bytes for binary files."""

    content = path.read_bytes()
    if b"\0" in content:
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _manifest_entry(path: Path, root: Path) -> dict[str, Any]:
    content = _canonical_file_bytes(path)
    return {
        "path": _relative_path(path, root),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def _scan_secret_strings(path: str, content: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(content):
            if label == "credentialed database URL" and match.group().lower().endswith(
                ("@localhost", "@127.0.0.1")
            ):
                continue
            findings.append(f"{path} contains a secret-looking {label}")
            break
    return findings


def build_manifest(root: Path = ROOT, *, generated_at: str | None = None) -> dict[str, Any]:
    """Build a deterministic manifest for safe repository import."""

    timestamp = generated_at or datetime.now(UTC).isoformat()
    files = [_manifest_entry(path, root) for path in _iter_handoff_files(root)]
    return {
        "generated_at": timestamp,
        "purpose": "Verify the local source/config/docs handoff into the canonical Git repository.",
        # The manifest must survive a clone, worktree, archive, or handoff to a
        # different absolute path. All file entries are already repository-relative.
        "root": ".",
        "excluded_mutable_or_secret_paths": [
            ".coverage",
            ".env*",
            ".git/",
            ".vercel/",
            ".venv/",
            "artifacts/agent/",
            SELF_PATH,
            "data/",
            "media/",
            "node_modules/",
            "screenshots/",
            "web/coverage/",
            "web/dist/",
        ],
        "file_count": len(files),
        "files": files,
    }


def validate_manifest(document: dict[str, Any], root: Path = ROOT) -> list[str]:
    """Return manifest validation findings."""

    findings: list[str] = []
    generated_at = document.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        findings.append("repository handoff manifest generated_at must be a string")
        generated_at = "1970-01-01T00:00:00+00:00"

    expected = build_manifest(root, generated_at=generated_at)
    for key in ("purpose", "root", "excluded_mutable_or_secret_paths", "file_count", "files"):
        if document.get(key) != expected[key]:
            findings.append(f"repository handoff manifest {key} is stale or invalid")

    files = document.get("files")
    if isinstance(files, list):
        seen: set[str] = set()
        for index, item in enumerate(files):
            path = item.get("path") if isinstance(item, dict) else None
            if not isinstance(path, str):
                findings.append(f"repository handoff manifest files[{index}].path must be a string")
                continue
            if path in seen:
                findings.append(f"repository handoff manifest duplicates {path}")
            seen.add(path)
            if _is_excluded_path(path):
                findings.append(f"repository handoff manifest includes excluded path {path}")
            full_path = root / path
            try:
                text = full_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            except OSError:
                continue
            findings.extend(_scan_secret_strings(path, text))
    else:
        findings.append("repository handoff manifest files must be a list")

    return findings


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("repository handoff manifest must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Rewrite the manifest")
    args = parser.parse_args()

    if args.write:
        manifest = build_manifest(args.root)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Repository handoff manifest written: {args.manifest}")
        return 0

    try:
        document = _load_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Repository handoff manifest verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_manifest(document, args.root)
    if findings:
        print("Repository handoff manifest verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Repository handoff manifest verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
