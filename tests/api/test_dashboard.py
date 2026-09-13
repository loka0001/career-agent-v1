from tests.conftest import TestContext, onboard_product


def test_dashboard_requires_authentication(context: TestContext) -> None:
    response = context.client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_dashboard_reports_catalog_and_journey_activity(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    onboard_product(context, headers, "DASH-1", price="750.00", stock="2")
    product = context.client.get("/api/v1/products/DASH-1").json()
    assert product["status"] == "draft"
    context.client.patch(
        "/api/v1/products/DASH-1", headers=headers, json={"description": "منتج للوحة المتابعة"}
    )
    context.client.post("/api/v1/products/DASH-1/activate", headers=headers)
    pack = context.client.post(
        "/api/v1/products/DASH-1/marketing-packs", headers=headers
    ).json()
    context.client.post(f"/api/v1/marketing-packs/{pack['id']}/approve", headers=headers)
    publish = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": "dash-publish-1"},
        json={"platforms": ["facebook", "instagram"]},
    )
    assert publish.status_code == 200
    context.client.post(
        "/api/v1/sales/assist",
        headers=headers,
        json={"message": "عايز سماعة للمذاكرة وميزانيتي 1500 جنيه"},
    )

    response = context.client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()

    assert body["products"]["total"] >= 25
    assert body["products"]["active"] >= 1
    assert body["products"]["low_stock"] >= 1
    assert float(body["products"]["inventory_value"]) > 0
    assert len(body["products"]["categories"]) >= 3

    assert body["content"]["total_packs"] >= 1
    assert body["content"]["published"] >= 1

    assert body["publishing"]["total"] >= 2
    assert body["publishing"]["succeeded"] >= 2
    assert body["publishing"]["facebook"] >= 1
    assert body["publishing"]["instagram"] >= 1

    assert body["sales"]["total_queries"] >= 1
    assert body["sales"]["recent"][0]["message"]
    assert body["sales"]["recent"][0]["intent"]

    assert any(item["product_id"] == "DASH-1" for item in body["low_stock_products"])
    assert body["recent_publications"][0]["product_name"]
    assert body["recent_publications"][0]["platform"] in {"facebook", "instagram"}
