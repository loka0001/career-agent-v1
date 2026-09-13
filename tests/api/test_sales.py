from tests.conftest import TestContext


def test_sales_requires_session(context: TestContext) -> None:
    context.client.cookies.clear()
    response = context.client.post(
        "/api/v1/sales/assist", json={"message": "سؤال بدون جلسة"}
    )
    assert response.status_code == 401


def test_sales_happy_path_budget_stock_and_citations(context: TestContext) -> None:
    context.login()
    response = context.client.post(
        "/api/v1/sales/assist",
        json={"message": "عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["need"]["intent"] == "product_search"
    assert len(payload["recommendations"]) <= 3
    assert payload["recommendations"][0]["product_id"] == "A101"
    for recommendation in payload["recommendations"]:
        assert recommendation["product"]["stock"] > 0
        assert float(recommendation["product"]["price"]) <= 1500
        assert f"product:{recommendation['product_id']}" in payload["citations"]


def test_sales_policy_no_match_and_out_of_domain(context: TestContext) -> None:
    context.login()
    policy = context.client.post("/api/v1/sales/assist", json={"message": "ما هي سياسة الاسترجاع؟"})
    assert policy.status_code == 200
    assert "policy:returns-ar-v1" in policy.json()["citations"]
    no_match = context.client.post(
        "/api/v1/sales/assist",
        json={"message": "عايز سماعة للمكالمات وميزانيتي 10 جنيه"},
    )
    assert no_match.status_code == 200
    assert no_match.json()["recommendations"] == []
    outside = context.client.post(
        "/api/v1/sales/assist", json={"message": "من فاز في مباراة الأمس؟"}
    )
    assert outside.status_code == 200
    assert outside.json()["need"]["intent"] == "unsupported"
    assert outside.json()["recommendations"] == []


def test_sales_schema_error_is_safe(context: TestContext) -> None:
    context.login()
    response = context.client.post("/api/v1/sales/assist", json={"message": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "schema_validation_error"
    assert response.json()["error"]["request_id"]
