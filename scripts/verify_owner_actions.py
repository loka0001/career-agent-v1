"""Validate owner-action handoff evidence without exposing secrets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "artifacts" / "production-readiness" / "owner-actions.md"
DEFAULT_PROVIDER_STATUS_PATH = ROOT / "artifacts" / "agent" / "provider-status.json"

REQUIRED_SECTIONS = (
    "## Current Sequential Blocker",
    "## Next Action After Git Is Restored",
    "## Later Provider Actions",
)
REQUIRED_FIELD_LABELS = (
    "Provider",
    "Exact page",
    "Exact account or project",
    "Exact field",
    "Value source",
    "Reason",
    "Expected result",
    "Verification step after completion",
)
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
PROVIDERS_REQUIRING_OWNER_ACTION = {
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


def _section(content: str, heading: str) -> str:
    start = content.find(heading)
    if start == -1:
        return ""
    next_heading = content.find("\n## ", start + len(heading))
    if next_heading == -1:
        return content[start:]
    return content[start:next_heading]


def _provider_required_keys(provider_document: dict[str, Any] | None) -> set[str]:
    if provider_document is None:
        return set()
    providers = provider_document.get("providers")
    if not isinstance(providers, list):
        return set()
    keys: set[str] = set()
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_name = provider.get("provider")
        if provider_name not in PROVIDERS_REQUIRING_OWNER_ACTION:
            continue
        key_names = provider.get("required_environment_key_names")
        if isinstance(key_names, list):
            keys.update(item for item in key_names if isinstance(item, str))
    return keys


def validate_owner_actions(
    content: str,
    provider_document: dict[str, Any] | None = None,
) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(content):
            findings.append(f"owner-actions.md contains a secret-looking {label}")
    for section in REQUIRED_SECTIONS:
        if section not in content:
            findings.append(f"missing section: {section}")

    for section in ("## Current Sequential Blocker", "## Next Action After Git Is Restored"):
        text = _section(content, section)
        if not text:
            continue
        for field in REQUIRED_FIELD_LABELS:
            if f"| {field} |" not in text:
                findings.append(f"{section} missing field: {field}")

    later = _section(content, "## Later Provider Actions")
    for provider in (
        "Managed PostgreSQL",
        "Resend email",
        "OpenAI",
        "Meta social publishing / inbox",
        "Meta / WhatsApp",
        "Commerce connectors",
        "Media storage / malware scanning",
        "Stripe",
        "Sentry alerting",
    ):
        if provider not in later:
            findings.append(f"later provider action missing: {provider}")

    if "secret value" not in content.lower() and "names only" not in content.lower():
        findings.append("owner-actions.md must explicitly forbid recording secret values")

    missing_keys = sorted(
        key for key in _provider_required_keys(provider_document) if key not in content
    )
    if missing_keys:
        findings.append(
            "owner-actions.md missing provider-required key names: " + ", ".join(missing_keys)
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--provider-status", type=Path, default=DEFAULT_PROVIDER_STATUS_PATH)
    args = parser.parse_args()

    try:
        content = args.path.read_text(encoding="utf-8")
        provider_document = json.loads(args.provider_status.read_text(encoding="utf-8"))
        if not isinstance(provider_document, dict):
            raise ValueError("provider status artifact must be a JSON object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Owner-action verification failed: {exc}", file=sys.stderr)
        return 1
    findings = validate_owner_actions(content, provider_document)
    if findings:
        print("Owner-action verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Owner-action verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
