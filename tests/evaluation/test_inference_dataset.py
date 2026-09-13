from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import TestContext

DATASET = json.loads(
    (
        Path(__file__).resolve().parents[2] / "data" / "seeds" / "evaluation_questions.json"
    ).read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", DATASET, ids=[item["id"] for item in DATASET])
def test_deterministic_inference_contract(case: dict[str, str], context: TestContext) -> None:
    context.login()
    response = context.client.post("/api/v1/sales/assist", json={"message": case["message"]})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["need"]["intent"] == case["expected_intent"]
    assert len(payload["recommendations"]) <= 3
    if "max_budget" in case:
        budget = float(case["max_budget"])
        assert all(float(item["product"]["price"]) <= budget for item in payload["recommendations"])
    recommended_ids = {item["product_id"] for item in payload["recommendations"]}
    assert all(
        citation.startswith("policy:") or citation.removeprefix("product:") in recommended_ids
        for citation in payload["citations"]
    )
