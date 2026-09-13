"""Multi-tenant registration, isolation, and RBAC tests."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.models import ConversationModel, CustomerModel, ProductModel
from app.services.opportunities import detect_opportunities
from tests.conftest import TestContext, latest_email_token


def _register(context: TestContext, *, email: str) -> tuple[dict[str, str], str]:
    """Register a fresh tenant; returns (csrf headers, store_id)."""

    response = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Rival Electronics",
            "store_name": "Rival Store",
            "email": email,
            "password": "another-strong-pass-123",
            "full_name": "Rival Owner",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "owner"
    return {"X-CSRF-Token": body["csrf_token"]}, body["user"]["store_id"]


def test_register_creates_isolated_tenant(context: TestContext) -> None:
    email = f"owner-{uuid.uuid4().hex[:8]}@rival.example"
    headers, store_id = _register(context, email=email)
    assert store_id != "demo-store"

    # The new tenant starts with an empty catalog, not the demo data.
    products = context.client.get("/api/v1/products")
    assert products.status_code == 200
    assert products.json() == []

    # Direct object reference to another store's product must fail.
    foreign = context.client.get("/api/v1/products/A101")
    assert foreign.status_code == 404

    stores = context.client.get("/api/v1/auth/stores")
    assert [item["store_id"] for item in stores.json()["stores"]] == [store_id]

    # Switching to a store outside the membership is forbidden.
    forbidden_switch = context.client.post(
        "/api/v1/auth/switch-store", headers=headers, json={"store_id": "demo-store"}
    )
    assert forbidden_switch.status_code == 403

    # Restore the demo session for the rest of the suite.
    context.login()


def test_duplicate_email_rejected(context: TestContext) -> None:
    email = f"dup-{uuid.uuid4().hex[:8]}@rival.example"
    _register(context, email=email)
    duplicate = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Copycat",
            "store_name": "Copy Store",
            "email": email,
            "password": "another-strong-pass-123",
        },
    )
    assert duplicate.status_code == 409
    context.login()


def test_dashboard_shows_only_own_store(context: TestContext) -> None:
    email = f"dash-{uuid.uuid4().hex[:8]}@rival.example"
    _register(context, email=email)
    dashboard = context.client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["products"]["total"] == 0
    context.login()


def test_demo_owner_still_logs_in_and_writes(context: TestContext) -> None:
    headers = context.login()
    me = context.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "owner"
    assert me.json()["user"]["store_id"] == "demo-store"
    # Owner passes the marketer gate used by catalog writes.
    response = context.client.patch(
        "/api/v1/products/A101", headers=headers, json={"description": "وصف محدث للاختبار"}
    )
    assert response.status_code == 200
    # Restore active status so seed-dependent tests keep their invariant.
    reactivated = context.client.post("/api/v1/products/A101/activate", headers=headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_new_resources_reject_cross_tenant_object_references(
    context: TestContext,
) -> None:
    owner_headers = context.login()
    with context.session_factory() as session:
        conversation_id = session.scalar(
            select(ConversationModel.id).where(
                ConversationModel.store_id == "demo-store"
            )
        )
        customer_id = session.scalar(
            select(CustomerModel.id).where(CustomerModel.store_id == "demo-store")
        )
        product_id = session.scalar(
            select(ProductModel.product_id).where(
                ProductModel.store_id == "demo-store",
                ProductModel.status == "active",
            )
        )
        assert conversation_id and customer_id and product_id

    order = context.client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={
            "conversation_id": conversation_id,
            "items": [{"product_id": product_id, "quantity": 1}],
            "discount": "0",
            "shipping": {},
        },
    )
    assert order.status_code == 201, order.text
    automation = context.client.post(
        "/api/v1/automations",
        headers=owner_headers,
        json={
            "name": "Isolation proof",
            "trigger_type": "scheduled",
            "actions": [
                {
                    "action_type": "raise_alert",
                    "config": {"message": "isolation"},
                }
            ],
        },
    )
    assert automation.status_code == 201, automation.text
    content = context.client.post(
        "/api/v1/studio/content/generate",
        headers=owner_headers,
        json={
            "product_id": product_id,
            "content_format": "sales_post",
            "platform": "facebook",
            "tone": "friendly",
        },
    )
    assert content.status_code == 201, content.text
    with context.session_factory.begin() as session:
        detect_opportunities(session, "demo-store")
    opportunities = context.client.get(
        "/api/v1/opportunities", headers=owner_headers
    ).json()
    assert opportunities
    team = context.client.get("/api/v1/team", headers=owner_headers).json()
    demo_owner = next(member for member in team if member["role"] == "owner")

    rival_headers, _ = _register(
        context, email=f"isolation-{uuid.uuid4().hex[:8]}@rival.example"
    )
    checks = [
        context.client.get(f"/api/v1/customers/{customer_id}"),
        context.client.get(f"/api/v1/orders/{order.json()['id']}"),
        context.client.post(
            f"/api/v1/opportunities/{opportunities[0]['id']}/decision",
            headers=rival_headers,
            json={"decision": "reject", "realized_revenue": "0"},
        ),
        context.client.post(
            f"/api/v1/automations/{automation.json()['id']}/disable",
            headers=rival_headers,
        ),
        context.client.patch(
            f"/api/v1/studio/content/{content.json()['id']}",
            headers=rival_headers,
            json={"caption": "must not cross tenants"},
        ),
        context.client.post(
            f"/api/v1/team/{demo_owner['membership_id']}/revoke",
            headers=rival_headers,
        ),
    ]
    assert all(response.status_code == 404 for response in checks)
    context.login()


def test_role_permission_matrix_for_new_product_areas(
    context: TestContext,
) -> None:
    owner_headers = context.login()
    invited: list[tuple[int, str, str]] = []
    for role in ("analyst", "agent", "marketer", "admin"):
        owner_headers = context.login()
        email = f"matrix-{role}-{uuid.uuid4().hex[:6]}@example.com"
        password = f"Matrix-{role}-Secure-2026!"
        response = context.client.post(
            "/api/v1/team",
            headers=owner_headers,
            json={
                "email": email,
                "full_name": f"Matrix {role}",
                "role": role,
            },
        )
        assert response.status_code == 201, response.text
        accepted = context.client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": latest_email_token(context, email),
                "password": password,
                "full_name": f"Matrix {role}",
            },
        )
        assert accepted.status_code == 200, accepted.text
        owner_headers = context.login()
        members = context.client.get("/api/v1/team", headers=owner_headers).json()
        member = next(item for item in members if item["email"] == email)
        invited.append(
            (
                member["membership_id"],
                email,
                password,
            )
        )

    expectations = {
        "analyst": (403, 403, 403),
        "agent": (202, 403, 403),
        "marketer": (202, 200, 403),
        "admin": (202, 200, 200),
    }
    for (_, email, password), role in zip(
        invited, expectations, strict=True
    ):
        login = context.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        scan = context.client.post(
            "/api/v1/opportunities/scan", headers=headers
        )
        brand = context.client.put(
            "/api/v1/studio/brand",
            headers=headers,
            json={
                "tone": "professional",
                "audience": "test",
                "guidelines": "",
                "primary_color": "#2563eb",
            },
        )
        automation = context.client.post(
            "/api/v1/automations/templates/low_stock_alert", headers=headers
        )
        assert (
            scan.status_code,
            brand.status_code,
            automation.status_code,
        ) == expectations[role]

    owner_headers = context.login()
    for membership_id, _, _ in invited:
        revoked = context.client.post(
            f"/api/v1/team/{membership_id}/revoke", headers=owner_headers
        )
        assert revoked.status_code == 200
