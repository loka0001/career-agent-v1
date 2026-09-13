"""Run unauthenticated smoke checks against a Preview or Production deployment."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from urllib.parse import urljoin


@dataclass(frozen=True)
class SmokeResponse:
    status: int
    headers: dict[str, str]
    body: bytes


Fetch = Callable[[str], SmokeResponse]

SECURITY_HEADERS = {
    "content-security-policy": "default-src 'self'",
    "strict-transport-security": "max-age=",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=()",
    "cross-origin-opener-policy": "same-origin-allow-popups",
}


def _header(headers: dict[str, str], name: str) -> str:
    lower = name.lower()
    for key, value in headers.items():
        if key.lower() == lower:
            return value
    return ""


def _json(response: SmokeResponse, path: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, f"{path} did not return valid JSON"
    if not isinstance(parsed, dict):
        return None, f"{path} returned a non-object JSON payload"
    return parsed, None


def urllib_fetch(url: str) -> SmokeResponse:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return SmokeResponse(
                status=response.status,
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        return SmokeResponse(
            status=exc.code,
            headers=dict(exc.headers.items()),
            body=exc.read(),
        )


def _expect_status(
    findings: list[str],
    path: str,
    response: SmokeResponse,
    expected: int,
) -> None:
    if response.status != expected:
        findings.append(f"{path} returned HTTP {response.status}, expected {expected}")


def _check_security_headers(findings: list[str], response: SmokeResponse) -> None:
    for header_name, expected_fragment in SECURITY_HEADERS.items():
        value = _header(response.headers, header_name)
        if expected_fragment not in value:
            findings.append(f"/ missing or invalid security header {header_name}")


def _check_live(findings: list[str], response: SmokeResponse) -> None:
    _expect_status(findings, "/health/live", response, HTTPStatus.OK)
    payload, error = _json(response, "/health/live")
    if error:
        findings.append(error)
        return
    if payload is None:
        findings.append("/health/live JSON payload is missing")
        return
    if payload.get("status") != "ok":
        findings.append("/health/live status is not ok")
    checks = payload.get("checks")
    if not isinstance(checks, dict) or checks.get("process") is not True:
        findings.append("/health/live process check is not true")


def _check_ready(findings: list[str], response: SmokeResponse) -> None:
    _expect_status(findings, "/health/ready", response, HTTPStatus.OK)
    payload, error = _json(response, "/health/ready")
    if error:
        findings.append(error)
        return
    if payload is None:
        findings.append("/health/ready JSON payload is missing")
        return
    if payload.get("status") != "ok":
        findings.append("/health/ready status is not ok")
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        findings.append("/health/ready checks payload is missing")
        return
    for check_name in ("database", "search", "job_queue"):
        if checks.get(check_name) is not True:
            findings.append(f"/health/ready {check_name} check is not true")


def _check_json_404(findings: list[str], path: str, response: SmokeResponse) -> None:
    _expect_status(findings, path, response, HTTPStatus.NOT_FOUND)
    content_type = _header(response.headers, "content-type")
    if "application/json" not in content_type.lower():
        findings.append(f"{path} did not return JSON")
    cache_control = _header(response.headers, "cache-control")
    if "no-store" not in cache_control.lower():
        findings.append(f"{path} did not return Cache-Control: no-store")
    payload, error = _json(response, path)
    if error:
        findings.append(error)
        return
    if payload is None:
        findings.append(f"{path} JSON payload is missing")
        return
    error_payload = payload.get("error")
    if not isinstance(error_payload, dict) or error_payload.get("code") != "not_found":
        findings.append(f"{path} did not return error.code=not_found")


def verify_deployment_smoke(base_url: str, *, fetch: Fetch = urllib_fetch) -> list[str]:
    """Return findings for public deployment smoke checks."""

    normalized_base = base_url.rstrip("/") + "/"
    findings: list[str] = []

    root = fetch(normalized_base)
    _expect_status(findings, "/", root, HTTPStatus.OK)
    _check_security_headers(findings, root)

    _check_live(findings, fetch(urljoin(normalized_base, "health/live")))
    _check_ready(findings, fetch(urljoin(normalized_base, "health/ready")))
    _check_json_404(findings, "/openapi.json", fetch(urljoin(normalized_base, "openapi.json")))
    _check_json_404(
        findings,
        "/api/v1/conversations",
        fetch(urljoin(normalized_base, "api/v1/conversations")),
    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Preview or Production deployment base URL")
    args = parser.parse_args()

    findings = verify_deployment_smoke(args.url)
    if findings:
        print("Deployment smoke verification failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Deployment smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
