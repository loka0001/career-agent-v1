from __future__ import annotations

import uuid

from app.security import totp_code
from tests.conftest import TestContext, latest_email_token


def _register(context: TestContext) -> tuple[str, str, dict[str, str]]:
    email = f"auth-{uuid.uuid4().hex[:8]}@example.com"
    password = "Original-Secure-Password-2026!"
    response = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Auth Lifecycle Organization",
            "store_name": "Auth Lifecycle Store",
            "email": email,
            "password": password,
            "full_name": "Auth Owner",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["verification_required"] is False
    return email, password, {"X-CSRF-Token": response.json()["csrf_token"]}


def test_password_reset_is_generic_one_time_and_revokes_sessions(
    context: TestContext,
) -> None:
    email, password, _ = _register(context)
    context.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    forgot = context.client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert forgot.status_code == 200
    assert forgot.json()["message"] == "reset_sent_if_account_exists"
    token = latest_email_token(context, email)
    new_password = "Updated-Secure-Password-2026!"
    reset = context.client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": new_password},
    )
    assert reset.status_code == 200, reset.text
    assert context.client.get("/api/v1/auth/me").status_code == 401
    assert (
        context.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        ).status_code
        == 401
    )
    login = context.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert login.status_code == 200, login.text
    replay = context.client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "Replay-Secure-Password-2026!"},
    )
    assert replay.status_code == 401


def test_sessions_are_listed_and_server_revoke_is_immediate(
    context: TestContext,
) -> None:
    email, password, _ = _register(context)
    second = context.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert second.status_code == 200
    headers = {"X-CSRF-Token": second.json()["csrf_token"]}
    sessions = context.client.get("/api/v1/auth/sessions").json()
    assert len(sessions) == 2
    current = next(item for item in sessions if item["current"])
    revoked = context.client.post(
        f"/api/v1/auth/sessions/{current['session_id']}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200
    assert context.client.get("/api/v1/auth/me").status_code == 401


def test_totp_mfa_is_required_after_confirmation(context: TestContext) -> None:
    email, password, headers = _register(context)
    setup = context.client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    confirmed = context.client.post(
        "/api/v1/auth/mfa/confirm",
        headers=headers,
        json={"code": totp_code(secret)},
    )
    assert confirmed.status_code == 200, confirmed.text
    context.client.post("/api/v1/auth/logout", headers=headers)

    challenge = context.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert challenge.status_code == 401
    assert challenge.json()["error"]["code"] == "mfa_required"
    login = context.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "otp": totp_code(secret)},
    )
    assert login.status_code == 200, login.text
