"""Deterministic product filters and explainable ranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import CustomerNeed, ProductRecord

TOKEN_PATTERN = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
TOKEN_ALIASES = {
    "mic": "microphone",
    "ميكروفون": "microphone",
    "بلوتوث": "bluetooth",
    "wireless": "bluetooth",
    "لاسلكي": "bluetooth",
    "مريح": "comfortable",
    "مريحة": "comfortable",
    "مكالمات": "calls",
    "للمكالمات": "calls",
    "meeting": "calls",
    "اجتماعات": "calls",
    "مذاكرة": "studying",
    "للمذاكرة": "studying",
    "دراسة": "studying",
    "التعلم": "studying",
    "سفر": "travel",
    "السفر": "travel",
    "رحلات": "travel",
    "منزل": "home",
    "المنزل": "home",
    "بيت": "home",
}


def normalize_tokens(values: list[str] | str) -> set[str]:
    text = " ".join(values) if isinstance(values, list) else values
    raw_tokens = {token.casefold() for token in TOKEN_PATTERN.findall(text) if len(token) > 1}
    return raw_tokens | {TOKEN_ALIASES[token] for token in raw_tokens if token in TOKEN_ALIASES}


def apply_business_filters(
    products: list[ProductRecord], need: CustomerNeed
) -> list[ProductRecord]:
    """Apply authoritative stock, budget, category, and exclusion rules."""

    allowed_categories = {item.casefold() for item in need.categories}
    excluded = normalize_tokens(need.excluded_features)
    accepted: list[ProductRecord] = []
    for product in products:
        if product.stock <= 0:
            continue
        if need.max_budget is not None and product.price > need.max_budget:
            continue
        if allowed_categories and product.category.casefold() not in allowed_categories:
            continue
        product_tokens = normalize_tokens(
            product.features + product.customer_benefits + [product.description]
        )
        if excluded and excluded.intersection(product_tokens):
            continue
        accepted.append(product)
    return accepted


@dataclass(frozen=True)
class RankingScore:
    total: float
    feature_match: float
    budget_match: float
    use_case_match: float
    reasons: tuple[str, ...]


def _ratio(required: set[str], available: set[str]) -> float:
    if not required:
        return 1.0
    return len(required.intersection(available)) / len(required)


def score_product(product: ProductRecord, need: CustomerNeed) -> RankingScore:
    facts = normalize_tokens(
        product.features
        + product.customer_benefits
        + [product.name, product.category, product.description]
    )
    required = normalize_tokens(need.required_features)
    use_cases = normalize_tokens(need.use_cases)
    feature_match = _ratio(required, facts)
    use_case_match = _ratio(use_cases, facts)
    budget_match = 1.0
    if need.max_budget is not None:
        remaining = max(Decimal("0"), need.max_budget - product.price)
        budget_match = float(Decimal("0.5") + Decimal("0.5") * remaining / need.max_budget)
    total = feature_match * 0.50 + budget_match * 0.25 + use_case_match * 0.25

    reasons: list[str] = []
    matched_features = sorted(required.intersection(facts))
    matched_uses = sorted(use_cases.intersection(facts))
    if matched_features:
        reasons.append("يطابق الخصائص المطلوبة: " + "، ".join(matched_features[:3]))
    if matched_uses:
        reasons.append("مناسب للاستخدام: " + "، ".join(matched_uses[:3]))
    if need.max_budget is not None:
        reasons.append(f"داخل الميزانية بسعر {product.price} جنيه")
    if not reasons:
        reasons.append("متاح حاليًا ومرتبط بطلبك")
    return RankingScore(
        total=round(min(1.0, max(0.0, total)), 4),
        feature_match=feature_match,
        budget_match=budget_match,
        use_case_match=use_case_match,
        reasons=tuple(reasons),
    )


def rank_products(
    products: list[ProductRecord], need: CustomerNeed, *, limit: int = 3
) -> list[tuple[ProductRecord, RankingScore]]:
    scored = [(product, score_product(product, need)) for product in products]
    scored.sort(key=lambda item: (-item[1].total, item[0].price, item[0].product_id))
    return scored[:limit]
