from __future__ import annotations

import uuid

from tests.conftest import PNG_BYTES, TestContext, onboard_product


def test_product_endpoints_and_invalid_file(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    products = context.client.get("/api/v1/products")
    assert products.status_code == 200
    assert len(products.json()) >= 24
    missing = context.client.get("/api/v1/products/DOES-NOT-EXIST")
    assert missing.status_code == 404
    invalid = context.client.post(
        "/api/v1/products/onboard",
        headers=headers,
        data={
            "product_id": "BADFILE",
            "name": "Bad File",
            "category": "Audio",
            "price": "100",
            "stock": "1",
            "raw_features": "[]",
        },
        files={"image": ("fake.png", b"not-an-image", "image/png")},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_input"
    bad_features = context.client.post(
        "/api/v1/products/onboard",
        headers=headers,
        data={
            "product_id": "BADJSON",
            "name": "Bad JSON",
            "category": "Audio",
            "price": "100",
            "stock": "1",
            "raw_features": "not-json",
        },
        files={"image": ("fake.png", PNG_BYTES, "image/png")},
    )
    assert bad_features.status_code == 400
    oversized = context.client.post(
        "/api/v1/products/onboard",
        headers=headers,
        data={
            "product_id": "TOOLARGE",
            "name": "Too Large",
            "category": "Audio",
            "price": "100",
            "stock": "1",
            "raw_features": "[]",
        },
        files={
            "image": (
                "large.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * 1024,
                "image/png",
            )
        },
    )
    assert oversized.status_code == 400
    assert oversized.json()["error"]["details"]["max_bytes"] == 1024


def test_approval_gate_edit_invalidation_and_idempotency(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    product_id = f"FLOW{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id)
    assert context.client.get(f"/api/v1/products/{product_id}").status_code == 200
    review = context.client.patch(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={"description": "Reviewed grounded product description."},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "reviewed"
    activate = context.client.post(f"/api/v1/products/{product_id}/activate", headers=headers)
    assert activate.status_code == 200
    pack_response = context.client.post(
        f"/api/v1/products/{product_id}/marketing-packs", headers=headers
    )
    assert pack_response.status_code == 201, pack_response.text
    pack = pack_response.json()
    get_pack = context.client.get(f"/api/v1/marketing-packs/{pack['id']}")
    assert get_pack.status_code == 200
    missing_key = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers=headers,
        json={"platforms": ["facebook"]},
    )
    assert missing_key.status_code == 422
    key = f"request-{uuid.uuid4().hex}"
    blocked = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": key},
        json={"platforms": ["facebook"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "content_not_approved"
    approved = context.client.post(f"/api/v1/marketing-packs/{pack['id']}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == "merchant@example.com"
    edited = context.client.patch(
        f"/api/v1/marketing-packs/{pack['id']}",
        headers=headers,
        json={"facebook_message": "Edited factual content without a price."},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "draft"
    blocked_after_edit = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": key},
        json={"platforms": ["facebook"]},
    )
    assert blocked_after_edit.status_code == 409
    context.client.post(f"/api/v1/marketing-packs/{pack['id']}/approve", headers=headers)
    first = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": key},
        json={"platforms": ["facebook", "instagram"]},
    )
    assert first.status_code == 200, first.text
    assert all(item["success"] and item["raw_status"] == "DEMO" for item in first.json()["results"])
    second = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": key},
        json={"platforms": ["facebook", "instagram"]},
    )
    assert second.status_code == 200
    assert second.json() == first.json()
    publication_id = first.json()["results"][0]["publication_id"]
    assert context.client.get(f"/api/v1/publications/{publication_id}").status_code == 200


def test_integrations_are_secret_safe(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    status = context.client.get("/api/v1/integrations")
    assert status.status_code == 200
    serialized = status.text
    assert "access_token" not in serialized
    checked = context.client.post("/api/v1/integrations/meta/check", headers=headers)
    assert checked.status_code == 200
    checked_statuses = {item["name"]: item for item in checked.json()["integrations"]}
    assert checked_statuses["facebook"]["configured"] is True
    assert checked_statuses["instagram"]["configured"] is True
    assert checked_statuses["meta_social_connections"]["mode"] in {
        "connected",
        "disconnected",
    }
    assert "demo-token" not in checked.text
