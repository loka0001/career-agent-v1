from __future__ import annotations

import json
from collections.abc import Callable

from scripts.verify_deployment_smoke import SmokeResponse, verify_deployment_smoke


def _response(
    status: int,
    body: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
) -> SmokeResponse:
    return SmokeResponse(
        status=status,
        headers=headers or {"content-type": "application/json"},
        body=json.dumps(body).encode("utf-8"),
    )


def _passing_fetch() -> Callable[[str], SmokeResponse]:
    security_headers = {
        "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
        "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
        "permissions-policy": "camera=(), microphone=(), geolocation=()",
        "cross-origin-opener-policy": "same-origin-allow-popups",
    }

    def fetch(url: str) -> SmokeResponse:
        if url.endswith("/"):
            return _response(200, {"html": "ok"}, headers=security_headers)
        if url.endswith("/health/live"):
            return _response(200, {"status": "ok", "checks": {"process": True}})
        if url.endswith("/health/ready"):
            return _response(
                200,
                {
                    "status": "ok",
                    "checks": {"database": True, "search": True, "job_queue": True},
                },
            )
        if url.endswith("/openapi.json") or url.endswith("/api/v1/conversations"):
            return _response(
                404,
                {"error": {"code": "not_found"}},
                headers={"content-type": "application/json", "cache-control": "no-store"},
            )
        raise AssertionError(f"Unexpected URL {url}")

    return fetch


def test_deployment_smoke_accepts_expected_public_responses() -> None:
    assert verify_deployment_smoke("https://commerce.example.com", fetch=_passing_fetch()) == []


def test_deployment_smoke_rejects_old_html_api_fallback() -> None:
    def fetch(url: str) -> SmokeResponse:
        if url.endswith("/api/v1/conversations"):
            return SmokeResponse(
                status=503,
                headers={"content-type": "text/html"},
                body=b"<!doctype html><title>Service unavailable</title>",
            )
        return _passing_fetch()(url)

    findings = verify_deployment_smoke("https://commerce.example.com", fetch=fetch)

    assert "/api/v1/conversations returned HTTP 503, expected 404" in findings
    assert "/api/v1/conversations did not return JSON" in findings


def test_deployment_smoke_rejects_degraded_readiness() -> None:
    def fetch(url: str) -> SmokeResponse:
        if url.endswith("/health/ready"):
            return _response(
                503,
                {
                    "status": "degraded",
                    "checks": {"database": True, "search": True, "job_queue": False},
                },
            )
        return _passing_fetch()(url)

    findings = verify_deployment_smoke("https://commerce.example.com", fetch=fetch)

    assert "/health/ready returned HTTP 503, expected 200" in findings
    assert "/health/ready job_queue check is not true" in findings
