from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_provider_status import load_json, validate_provider_status

ROOT = Path(__file__).resolve().parents[2]


def test_current_provider_status_artifact_is_valid() -> None:
    document = load_json(ROOT / "artifacts" / "agent" / "provider-status.json")

    assert validate_provider_status(document) == []


def test_provider_status_rejects_invalid_status_value() -> None:
    document = load_json(ROOT / "artifacts" / "agent" / "provider-status.json")
    changed = deepcopy(document)
    changed["providers"][0]["status"] = "readyish"

    assert "$.providers[0].status has invalid value" in validate_provider_status(changed)


def test_provider_status_rejects_secret_like_values() -> None:
    document = load_json(ROOT / "artifacts" / "agent" / "provider-status.json")
    changed = deepcopy(document)
    fake_secret = "sk-" + "test_secret1234567890abcd"
    changed["providers"][0]["last_test"] = f"accidentally pasted {fake_secret}"

    findings = validate_provider_status(changed)

    assert any("secret-looking OpenAI key" in finding for finding in findings)


def test_provider_status_rejects_environment_values_in_key_names() -> None:
    document = load_json(ROOT / "artifacts" / "agent" / "provider-status.json")
    changed = deepcopy(document)
    changed["providers"][0]["required_environment_key_names"] = ["VERCEL_TOKEN=secret"]

    assert (
        "$.providers[0].required_environment_key_names must contain names only"
        in validate_provider_status(changed)
    )
