"""Validate the committed environment-variable template."""

from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.verify_environment_matrix import CRITICAL_RUNTIME_KEYS
from scripts.verify_provider_status import DEFAULT_STATUS_PATH, SECRET_PATTERNS, load_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_EXAMPLE_PATH = ROOT / ".env.example"

VARIABLE_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
SENSITIVE_NAME_PATTERN = re.compile(
    r"(?:^|_)(?:API_KEY|SECRET|TOKEN|PASSWORD|PASSWORD_HASH|DSN)(?:$|_)",
)
NON_SECRET_TEMPLATE_VALUES = {
    "APP_ENV",
    "DEMO_MODE",
    "DATABASE_URL",
    "DATABASE_POOL_SIZE",
    "DATABASE_MAX_OVERFLOW",
    "DATABASE_POOL_RECYCLE_SECONDS",
    "UPLOAD_DIRECTORY",
    "CHROMA_DIRECTORY",
    "SEARCH_PROVIDER",
    "SERVERLESS_MODE",
    "PUBLIC_BASE_URL",
    "ALLOWED_ORIGINS",
    "DEMO_STORE_ID",
    "AI_PROVIDER",
    "OPENAI_MODEL",
    "AI_TIMEOUT_SECONDS",
    "AI_CIRCUIT_FAILURE_THRESHOLD",
    "AI_CIRCUIT_OPEN_SECONDS",
    "AI_INPUT_COST_PER_MILLION_USD",
    "AI_OUTPUT_COST_PER_MILLION_USD",
    "IMAGE_STORAGE_PROVIDER",
    "CLOUDINARY_TIMEOUT_SECONDS",
    "MALWARE_SCANNER",
    "CLAMAV_HOST",
    "CLAMAV_PORT",
    "MALWARE_SCAN_TIMEOUT_SECONDS",
    "ENABLE_FAKE_PUBLISHING",
    "ENABLE_REAL_PUBLISHING",
    "META_GRAPH_API_BASE",
    "META_GRAPH_API_VERSION",
    "META_OAUTH_REDIRECT_URI",
    "META_REQUEST_TIMEOUT_SECONDS",
    "META_POLL_INTERVAL_SECONDS",
    "META_POLL_TIMEOUT_SECONDS",
    "SHOPIFY_API_VERSION",
    "COMMERCE_REQUEST_TIMEOUT_SECONDS",
    "RUN_META_SMOKE_TESTS",
    "RUN_LIVE_AI_EVALS",
    "FREE_ACCESS_MODE",
    "BILLING_PROVIDER",
    "STRIPE_REQUEST_TIMEOUT_SECONDS",
    "PAYMENT_PROVIDER",
    "EMAIL_PROVIDER",
    "INTEGRATION_ENCRYPTION_KEY_VERSION",
    "ENABLE_BACKGROUND_WORKER",
    "WORKER_POLL_SECONDS",
    "WORKER_LEASE_SECONDS",
    "WORKER_HEALTH_PORT",
    "MAX_IMAGE_BYTES",
    "MAX_CHANNEL_MEDIA_BYTES",
    "MAX_CUSTOMER_MESSAGE_LENGTH",
    "RETRIEVAL_MIN_SCORE",
    "SESSION_TTL_SECONDS",
    "COOKIE_SECURE",
    "EXPECTED_MIGRATION_HEAD",
}


def parse_env_example(template: str) -> tuple[dict[str, str], list[str]]:
    """Parse a simple KEY=value env template without expanding values."""

    values: dict[str, str] = {}
    findings: list[str] = []
    for line_number, line in enumerate(template.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            findings.append(f".env.example line {line_number} must use KEY=value syntax")
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not VARIABLE_NAME_PATTERN.fullmatch(key):
            findings.append(f".env.example line {line_number} has invalid key name")
            continue
        if key in values:
            findings.append(f".env.example line {line_number} duplicates {key}")
        values[key] = value.strip()
    return values, findings


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


def _scan_secret_strings(template: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(template):
            findings.append(f".env.example contains a secret-looking {label}")
    return findings


def validate_env_example(
    template: str,
    provider_document: dict[str, Any],
) -> list[str]:
    """Return validation findings for .env.example without printing values."""

    findings = _scan_secret_strings(template)
    values, parse_findings = parse_env_example(template)
    findings.extend(parse_findings)

    required = CRITICAL_RUNTIME_KEYS | _provider_required_keys(provider_document)
    missing = sorted(required - set(values))
    if missing:
        findings.append(".env.example missing required keys: " + ", ".join(missing))

    for key, value in values.items():
        if not value:
            continue
        if SENSITIVE_NAME_PATTERN.search(key) and key not in NON_SECRET_TEMPLATE_VALUES:
            findings.append(f".env.example {key} must not include a committed value")
    return findings


def template_is_git_ignored(root: Path = ROOT) -> bool:
    """Return whether Git ignore rules would exclude the committed template."""

    if not (root / ".git").exists():
        return False
    if shutil.which("git") is not None:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", ".env.example"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    ignored = False
    ignore_file = root / ".gitignore"
    if not ignore_file.is_file():
        return ignored
    for raw_pattern in ignore_file.read_text(encoding="utf-8").splitlines():
        pattern = raw_pattern.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        candidate = pattern[1:] if negated else pattern
        candidate = candidate.removeprefix("/").removesuffix("/")
        if fnmatch.fnmatchcase(".env.example", candidate):
            ignored = not negated
    return ignored


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_ENV_EXAMPLE_PATH,
        help="Path to the committed .env.example template",
    )
    parser.add_argument(
        "--provider-status",
        type=Path,
        default=DEFAULT_STATUS_PATH,
        help="Path to artifacts/agent/provider-status.json",
    )
    args = parser.parse_args()

    try:
        template = args.path.read_text(encoding="utf-8")
        provider_document = load_json(args.provider_status)
    except (OSError, ValueError) as exc:
        print(f"Environment template verification failed: {exc}", file=sys.stderr)
        return 1

    findings = validate_env_example(template, provider_document)
    if template_is_git_ignored(args.path.resolve().parent):
        findings.append(".env.example must not be excluded by Git ignore rules")
    if findings:
        print("Environment template verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Environment template verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
