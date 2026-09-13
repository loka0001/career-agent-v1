from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.verify_env_example import (
    parse_env_example,
    template_is_git_ignored,
    validate_env_example,
)
from scripts.verify_provider_status import load_json

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE_PATH = ROOT / ".env.example"
PROVIDER_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"


def test_current_env_example_is_valid() -> None:
    template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)

    assert validate_env_example(template, provider_document) == []
    assert template_is_git_ignored() is False


def test_env_example_rejects_missing_provider_required_key() -> None:
    template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)
    changed = deepcopy(provider_document)
    changed["providers"][0]["required_environment_key_names"].append(
        "NEW_PROVIDER_REQUIRED_KEY",
    )

    findings = validate_env_example(template, changed)

    assert ".env.example missing required keys: NEW_PROVIDER_REQUIRED_KEY" in findings


def test_env_example_rejects_secret_like_values() -> None:
    template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    provider_document = load_json(PROVIDER_PATH)
    fake_secret = "sk-" + "test_secret1234567890abcd"

    findings = validate_env_example(
        f"{template}\nOPENAI_API_KEY={fake_secret}\n",
        provider_document,
    )

    assert any("secret-looking OpenAI key" in finding for finding in findings)


def test_env_example_rejects_committed_sensitive_placeholder_value() -> None:
    template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").replace(
        "VERCEL_TOKEN=",
        "VERCEL_TOKEN=filled-in",
        1,
    )
    provider_document = load_json(PROVIDER_PATH)

    assert ".env.example VERCEL_TOKEN must not include a committed value" in validate_env_example(
        template, provider_document
    )


def test_env_example_parser_rejects_duplicate_keys() -> None:
    values, findings = parse_env_example("APP_ENV=development\nAPP_ENV=production\n")

    assert values["APP_ENV"] == "production"
    assert ".env.example line 2 duplicates APP_ENV" in findings


def test_env_example_ignore_check_works_without_git(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text(".env*\n!.env.example\n", encoding="utf-8")
    monkeypatch.setattr("scripts.verify_env_example.shutil.which", lambda _name: None)

    assert template_is_git_ignored(tmp_path) is False

    (tmp_path / ".gitignore").write_text(".env*\n", encoding="utf-8")
    assert template_is_git_ignored(tmp_path) is True
