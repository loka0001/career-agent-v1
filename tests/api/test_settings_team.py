from __future__ import annotations

from tests.conftest import latest_email_token


def test_store_settings_persist_agent_and_derives_onboarding_configuration(authenticated) -> None:
    context, headers = authenticated
    current = context.client.get("/api/v1/settings/store", headers=headers)
    assert current.status_code == 200, current.text
    payload = {
        key: value
        for key, value in current.json().items()
        if key
        not in {
            "store_id",
            "slug",
            "updated_at",
            "onboarding_steps",
            "onboarding_completed",
        }
    }
    payload.update(
        {
            "business_type": "electronics",
            "tone": "professional",
            "assistant_name": "مساعد الاختبار",
            "assistant_instructions": "اعتمد على الكتالوج فقط.",
            "shipping_policy": "الشحن خلال يومين.",
            "return_policy": "الاسترجاع خلال 14 يوماً.",
        }
    )
    saved = context.client.put(
        "/api/v1/settings/store", headers=headers, json=payload
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["assistant_name"] == "مساعد الاختبار"
    assert saved.json()["onboarding_steps"]["policies"] is True

    forged = {**payload, "onboarding_completed": True}
    rejected = context.client.put("/api/v1/settings/store", headers=headers, json=forged)
    assert rejected.status_code == 422


def test_team_invite_role_change_and_revoke(authenticated) -> None:
    context, headers = authenticated
    invited = context.client.post(
        "/api/v1/team",
        headers=headers,
        json={
            "email": "phase15-agent@example.com",
            "full_name": "Phase 15 Agent",
            "role": "agent",
        },
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    assert body["status"] == "pending"
    assert "temporary_password" not in body
    token = latest_email_token(context, "phase15-agent@example.com")
    accepted = context.client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token,
            "password": "Agent-Secure-Password-2026!",
            "full_name": "Phase 15 Agent",
        },
    )
    assert accepted.status_code == 200, accepted.text

    headers = context.login()
    members = context.client.get("/api/v1/team", headers=headers)
    member = next(
        item for item in members.json() if item["email"] == "phase15-agent@example.com"
    )
    membership_id = member["membership_id"]

    changed = context.client.patch(
        f"/api/v1/team/{membership_id}",
        headers=headers,
        json={"role": "marketer"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "marketer"

    revoked = context.client.post(
        f"/api/v1/team/{membership_id}/revoke", headers=headers
    )
    assert revoked.status_code == 200, revoked.text
    members = context.client.get("/api/v1/team", headers=headers)
    assert all(
        member["membership_id"] != membership_id for member in members.json()
    )
