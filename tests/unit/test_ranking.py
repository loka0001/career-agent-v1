from decimal import Decimal

from app.domain.models import CustomerNeed
from app.domain.ranking import (
    apply_business_filters,
    normalize_tokens,
    rank_products,
    score_product,
)
from tests.unit.test_validators import product


def test_filters_remove_out_of_stock_and_over_budget_products() -> None:
    need = CustomerNeed(intent="product_search", max_budget=Decimal("1000"))
    accepted = apply_business_filters(
        [product("A1", "900", 2), product("A2", "1100", 2), product("A3", "800", 0)],
        need,
    )
    assert [item.product_id for item in accepted] == ["A1"]


def test_ranking_exposes_components_and_uses_stable_tie_break() -> None:
    need = CustomerNeed(
        intent="product_search",
        max_budget=Decimal("1500"),
        required_features=["microphone"],
        use_cases=["calls"],
    )
    score = score_product(product("A2", "1000"), need)
    assert 0 <= score.total <= 1
    assert score.feature_match == 1
    ranked = rank_products([product("B2", "1000"), product("A1", "1000")], need)
    assert [item[0].product_id for item in ranked] == ["A1", "B2"]


def test_category_and_exclusion_are_authoritative() -> None:
    need = CustomerNeed(
        intent="product_search", categories=["Skincare"], excluded_features=["fragrance"]
    )
    assert apply_business_filters([product()], need) == []


def test_arabic_and_english_feature_tokens_share_a_canonical_match() -> None:
    assert "microphone" in normalize_tokens("ميكروفون للمكالمات")
    assert "calls" in normalize_tokens("ميكروفون للمكالمات")
    assert "bluetooth" in normalize_tokens("سماعة بلوتوث لاسلكية")
