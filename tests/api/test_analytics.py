from __future__ import annotations


def test_analytics_uses_real_store_data_and_supports_channel_filter(authenticated) -> None:
    context, headers = authenticated
    response = context.client.get("/api/v1/analytics", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversation_volume"] >= 3
    assert body["funnel"]["conversations"] == body["conversation_volume"]
    assert body["attributed_revenue"] is not None
    assert isinstance(body["orders_by_channel"], dict)
    assert isinstance(body["top_products"], list)
    assert body["ai_operations"] >= 0
    filtered = context.client.get(
        "/api/v1/analytics", headers=headers, params={"channel": "webchat"}
    )
    assert filtered.status_code == 200
    assert filtered.json()["channel"] == "webchat"
    assert (
        filtered.json()["conversation_volume"] <= body["conversation_volume"]
    )
