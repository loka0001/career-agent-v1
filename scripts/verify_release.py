"""Reject source releases containing credentials, local state, or dependency trees."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    ".env",
    ".mypy_cache",
    ".neon-deploy.env",
    ".pytest_cache",
    ".ruff_cache",
    ".vercel.production.env",
    "__pycache__",
    "node_modules",
    "commerce.db",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".pem",
    ".p12",
    ".pfx",
}
SKIP_DIRECTORIES = {
    ".git",
    ".vercel",
    ".venv",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "credentialed database URL": re.compile(
        r"\bpostgres(?:ql)?(?:\+psycopg)?://[^:\s/]+:[^@\s]+@[^\s/:]+",
        re.IGNORECASE,
    ),
    "Meta token": re.compile(r"\bEAA[A-Za-z0-9]{30,}\b"),
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        if path.is_dir():
            if path.name in FORBIDDEN_NAMES:
                findings.append(f"forbidden directory: {relative}")
            continue
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden file: {relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"unexpected binary file: {relative}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(content):
                if label == "credentialed database URL" and match.group().lower().endswith(
                    ("@localhost", "@127.0.0.1")
                ):
                    continue
                findings.append(f"{label}: {relative}")
                break
    if findings:
        print("Release verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Release source verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
