"""Validate the redacted provider activation evidence artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"

ALLOWED_STATUSES = {
    "production_verified",
    "configured_awaiting_external_activation",
    "blocked_missing_access",
    "blocked_legal_or_business_acceptance",
    "disabled",
    "not_applicable",
}
REQUIRED_PROVIDERS = {
    "vercel",
    "managed_postgresql",
    "postgres_backup_restore",
    "resend_email",
    "openai",
    "meta_social",
    "meta_whatsapp",
    "commerce_connectors",
    "media_malware",
    "stripe",
    "sentry_alerting",
}
REQUIRED_PROVIDER_FIELDS = {
    "provider",
    "status",
    "account_or_project_identifier",
    "required_environment_key_names",
    "required_keys_present",
    "last_test",
    "timestamp",
    "safe_external_event_or_request_id",
    "remaining_blocker",
    "exact_owner_action",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "credentialed database URL": re.compile(
        r"\bpostgres(?:ql)?(?:\+psycopg)?://[^:\s/]+:[^@\s]+@[^\s/:]+",
        re.IGNORECASE,
    ),
    "Meta token": re.compile(r"\bEAA[A-Za-z0-9]{30,}\b"),
    "Stripe key": re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "Resend key": re.compile(r"\bre_[A-Za-z0-9_-]{20,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
}


def _is_mapping(value: object) -> bool:
    return isinstance(value, dict)


def _parse_timestamp(value: object, path: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return f"{path} must be a non-empty ISO timestamp string"
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return f"{path} must be a valid ISO timestamp"
    return None


def _scan_secret_strings(value: object, path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(value, str):
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(value):
                findings.append(f"{path} contains a secret-looking {label}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_scan_secret_strings(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            findings.extend(_scan_secret_strings(item, f"{path}.{key}"))
    return findings


def validate_provider_status(document: dict[str, Any]) -> list[str]:
    """Return validation findings for provider-status.json without exposing values."""

    findings: list[str] = []
    findings.extend(_scan_secret_strings(document, "$"))

    timestamp_finding = _parse_timestamp(document.get("updated_at"), "$.updated_at")
    if timestamp_finding:
        findings.append(timestamp_finding)

    status_values = document.get("status_values")
    if not isinstance(status_values, list) or not all(
        isinstance(item, str) for item in status_values
    ):
        findings.append("$.status_values must be a list of status strings")
    elif set(status_values) != ALLOWED_STATUSES:
        findings.append("$.status_values must exactly match the allowed provider statuses")

    providers = document.get("providers")
    if not isinstance(providers, list):
        findings.append("$.providers must be a list")
        return findings

    seen: set[str] = set()
    for index, provider_record in enumerate(providers):
        path = f"$.providers[{index}]"
        if not _is_mapping(provider_record):
            findings.append(f"{path} must be an object")
            continue
        record = provider_record
        missing = REQUIRED_PROVIDER_FIELDS - set(record)
        if missing:
            findings.append(f"{path} is missing required fields: {', '.join(sorted(missing))}")

        provider = record.get("provider")
        if not isinstance(provider, str) or not provider:
            findings.append(f"{path}.provider must be a non-empty string")
            continue
        if provider in seen:
            findings.append(f"{path}.provider duplicates {provider}")
        seen.add(provider)

        status = record.get("status")
        if status not in ALLOWED_STATUSES:
            findings.append(f"{path}.status has invalid value")

        keys = record.get("required_environment_key_names")
        if not isinstance(keys, list) or not all(isinstance(item, str) for item in keys):
            findings.append(f"{path}.required_environment_key_names must be a list of strings")
        elif any("=" in item or not item.strip() for item in keys):
            findings.append(f"{path}.required_environment_key_names must contain names only")

        for text_field in (
            "account_or_project_identifier",
            "required_keys_present",
            "last_test",
            "remaining_blocker",
            "exact_owner_action",
        ):
            value = record.get(text_field)
            if not isinstance(value, str) or not value.strip():
                findings.append(f"{path}.{text_field} must be a non-empty string")

        event_id = record.get("safe_external_event_or_request_id")
        if event_id is not None and not isinstance(event_id, str):
            findings.append(f"{path}.safe_external_event_or_request_id must be null or a string")

        provider_timestamp_finding = _parse_timestamp(record.get("timestamp"), f"{path}.timestamp")
        if provider_timestamp_finding:
            findings.append(provider_timestamp_finding)

    missing_providers = REQUIRED_PROVIDERS - seen
    if missing_providers:
        findings.append(
            "missing required provider records: " + ", ".join(sorted(missing_providers))
        )
    return findings


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("provider status artifact must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_STATUS_PATH,
        help="Path to the redacted provider-status.json artifact",
    )
    args = parser.parse_args()

    try:
        document = load_json(args.path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Provider status verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_provider_status(document)
    if findings:
        print("Provider status verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Provider status verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
