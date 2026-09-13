"""Validate the redacted production environment-variable matrix."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from scripts.verify_provider_status import DEFAULT_STATUS_PATH, SECRET_PATTERNS, load_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_PATH = ROOT / "artifacts" / "production-readiness" / "environment-matrix.md"

EXPECTED_COLUMNS = (
    "Variable",
    "Purpose",
    "Required environments",
    "Current presence",
    "Secret",
    "Provider",
    "Rotation requirement",
    "Validation method",
)
CRITICAL_RUNTIME_KEYS = {
    "APP_ENV",
    "APP_SECRET_KEY",
    "DATABASE_URL",
    "CRON_SECRET",
    "INTEGRATION_ENCRYPTION_KEY",
    "PUBLIC_BASE_URL",
    "ALLOWED_ORIGINS",
    "COOKIE_SECURE",
    "ENABLE_BACKGROUND_WORKER",
    "OPERATOR_EMAILS",
    "RELEASE_SHA",
    "SENTRY_DSN",
}
VARIABLE_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
GENERATED_PATTERN = re.compile(r"^Generated:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _scan_secret_strings(value: str, path: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(value):
            findings.append(f"{path} contains a secret-looking {label}")
    return findings


def parse_environment_matrix(markdown: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse the environment matrix table and return rows plus structural findings."""

    findings: list[str] = []
    lines = markdown.splitlines()
    header_index: int | None = None
    for index, line in enumerate(lines):
        if _split_markdown_row(line) == list(EXPECTED_COLUMNS):
            header_index = index
            break
    if header_index is None:
        return [], ["environment-matrix.md must contain the expected variable table header"]

    if header_index + 1 >= len(lines) or not _is_separator_row(
        _split_markdown_row(lines[header_index + 1])
    ):
        findings.append("environment-matrix.md table must include a Markdown separator row")
        return [], findings

    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        if not line.strip():
            break
        if not line.lstrip().startswith("|"):
            break
        cells = _split_markdown_row(line)
        if len(cells) != len(EXPECTED_COLUMNS):
            findings.append(f"environment-matrix.md row {line_number} has malformed columns")
            continue
        rows.append(dict(zip(EXPECTED_COLUMNS, cells, strict=True)))

    if not rows:
        findings.append("environment-matrix.md must contain at least one variable row")
    return rows, findings


def _provider_required_keys(provider_document: dict[str, Any]) -> set[str]:
    providers = provider_document.get("providers")
    if not isinstance(providers, list):
        return set()
    keys: set[str] = set()
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        key_names = provider.get("required_environment_key_names")
        if isinstance(key_names, list):
            keys.update(item for item in key_names if isinstance(item, str))
    return keys


def validate_environment_matrix(
    markdown: str,
    provider_document: dict[str, Any],
) -> list[str]:
    """Return environment-matrix findings without exposing values."""

    findings: list[str] = []
    findings.extend(_scan_secret_strings(markdown, "environment-matrix.md"))

    generated_match = GENERATED_PATTERN.search(markdown)
    if generated_match is None:
        findings.append("environment-matrix.md must include a Generated: YYYY-MM-DD line")
    else:
        try:
            date.fromisoformat(generated_match.group(1))
        except ValueError:
            findings.append("environment-matrix.md Generated date must be valid ISO format")

    rows, table_findings = parse_environment_matrix(markdown)
    findings.extend(table_findings)

    seen: set[str] = set()
    variables: set[str] = set()
    for index, row in enumerate(rows):
        path = f"environment-matrix.md row {index + 1}"
        variable = row["Variable"]
        if not VARIABLE_NAME_PATTERN.fullmatch(variable):
            findings.append(f"{path} Variable must be an environment key name only")
        if "=" in variable:
            findings.append(f"{path} Variable must not contain an environment value")
        if variable in seen:
            findings.append(f"{path} duplicates variable {variable}")
        seen.add(variable)
        variables.add(variable)

        for column in EXPECTED_COLUMNS[1:]:
            value = row[column]
            if not value.strip():
                findings.append(f"{path} {column} must be non-empty")
            if "=" in value and column != "Validation method":
                findings.append(f"{path} {column} must not contain assignments or values")

        secret = row["Secret"].lower()
        if secret not in {"yes", "no"}:
            findings.append(f"{path} Secret must be yes or no")
        if secret == "yes" and row["Rotation requirement"].strip().lower() == "no":
            findings.append(f"{path} secret variables must define a rotation requirement")
        if variable.startswith(("NEXT_PUBLIC_", "VITE_")) and secret == "yes":
            findings.append(f"{path} browser-exposed variables must not be marked secret")

    required_keys = CRITICAL_RUNTIME_KEYS | _provider_required_keys(provider_document)
    missing = sorted(required_keys - variables)
    if missing:
        findings.append("environment-matrix.md missing required keys: " + ", ".join(missing))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_MATRIX_PATH,
        help="Path to artifacts/production-readiness/environment-matrix.md",
    )
    parser.add_argument(
        "--provider-status",
        type=Path,
        default=DEFAULT_STATUS_PATH,
        help="Path to artifacts/agent/provider-status.json",
    )
    args = parser.parse_args()

    try:
        markdown = args.path.read_text(encoding="utf-8")
        provider_document = load_json(args.provider_status)
    except (OSError, ValueError) as exc:
        print(f"Environment matrix verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_environment_matrix(markdown, provider_document)
    if findings:
        print("Environment matrix verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Environment matrix verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
