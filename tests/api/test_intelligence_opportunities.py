from __future__ import annotations

from sqlalchemy import select

from app.db.models import CustomerModel, ProductModel
from app.services.opportunities import detect_opportunities


def test_customer_intelligence_is_explainable_and_tenant_scoped(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory() as session:
        customer_id = session.scalar(
            select(CustomerModel.id).where(CustomerModel.store_id == "demo-store")
        )
        assert customer_id is not None
    response = context.client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lead_score"] == sum(
        signal["contribution"] for signal in body["score_signals"]
    )
    assert float(body["total_revenue"]) >= 0
    if body["completed_orders"]:
        assert any(signal["name"] == "purchases" for signal in body["score_signals"])
    assert context.client.get("/api/v1/customers/999999", headers=headers).status_code == 404


def test_opportunity_detection_dedup_and_lifecycle(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory.begin() as session:
        product = session.scalar(
            select(ProductModel).where(
                ProductModel.store_id == "demo-store",
                ProductModel.product_id == "A101",
            )
        )
        assert product is not None
        original_stock = product.stock
        product.stock = 2
    try:
        with context.session_factory.begin() as session:
            first = detect_opportunities(session, "demo-store")
            second = detect_opportunities(session, "demo-store")
            assert first >= 1
            assert second == 0

        listed = context.client.get("/api/v1/opportunities", headers=headers)
        assert listed.status_code == 200
        opportunity = next(
            item for item in listed.json() if item["opportunity_type"] == "low_stock"
        )
        opportunity_id = opportunity["id"]
        for decision, expected in [
            ("approve", "awaiting_approval"),
            ("execute", "executed"),
            ("won", "won"),
        ]:
            response = context.client.post(
                f"/api/v1/opportunities/{opportunity_id}/decision",
                headers=headers,
                json={
                    "decision": decision,
                    "realized_revenue": "1200" if decision == "won" else "0",
                },
            )
            assert response.status_code == 200, response.text
            assert response.json()["status"] == expected
        assert response.json()["realized_revenue"] == "1200.00"
    finally:
        with context.session_factory.begin() as session:
            product = session.scalar(
                select(ProductModel).where(
                    ProductModel.store_id == "demo-store",
                    ProductModel.product_id == "A101",
                )
            )
            assert product is not None
            product.stock = original_stock
