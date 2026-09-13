from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_environment_matrix import (
    CRITICAL_RUNTIME_KEYS,
    parse_environment_matrix,
    validate_environment_matrix,
)
from scripts.verify_provider_status import load_json

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "artifacts" / "production-readiness" / "environment-matrix.md"
PROVIDER_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"


def test_current_environment_matrix_is_valid() -> None:
    markdown = MATRIX_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)

    assert validate_environment_matrix(markdown, provider_document) == []


def test_environment_matrix_rejects_missing_provider_required_key() -> None:
    markdown = MATRIX_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)
    changed = deepcopy(provider_document)
    changed["providers"][0]["required_environment_key_names"].append(
        "NEW_PROVIDER_REQUIRED_KEY",
    )

    findings = validate_environment_matrix(markdown, changed)

    assert "environment-matrix.md missing required keys: NEW_PROVIDER_REQUIRED_KEY" in findings


def test_environment_matrix_rejects_secret_like_values() -> None:
    markdown = MATRIX_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)
    fake_secret = "sk-" + "test_secret1234567890abcd"

    findings = validate_environment_matrix(f"{markdown}\n{fake_secret}\n", provider_document)

    assert any("secret-looking OpenAI key" in finding for finding in findings)


def test_environment_matrix_rejects_assignment_in_variable_name() -> None:
    markdown = MATRIX_PATH.read_text(encoding="utf-8").replace(
        "| APP_ENV |",
        "| APP_ENV=production |",
        1,
    )
    provider_document = load_json(PROVIDER_PATH)

    findings = validate_environment_matrix(markdown, provider_document)

    assert any("Variable must be an environment key name only" in finding for finding in findings)


def test_environment_matrix_parser_reads_current_table() -> None:
    rows, findings = parse_environment_matrix(MATRIX_PATH.read_text(encoding="utf-8"))

    assert findings == []
    assert {row["Variable"] for row in rows} >= CRITICAL_RUNTIME_KEYS
