from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.errors import ConflictError
from app.domain.models import ProductUpdateInput
from app.repositories.policy_repository import PolicyRepository
from app.repositories.product_repository import ProductRepository
from tests.conftest import TestContext


def test_seed_is_queryable_and_indexed(context: TestContext) -> None:
    with context.session_factory() as session:
        products = ProductRepository(session).list("demo-store", active_only=True)
        policies = PolicyRepository(session).list("demo-store")
    assert len(products) >= 24
    assert {f"A{number}" for number in range(101, 107)}.issubset(
        {item.product_id for item in products}
    )
    assert len(policies) == 6
    hits = context.container.vector_store.search_products(
        "demo-store", "سماعة للمكالمات والمذاكرة", top_k=5
    )
    assert hits
    assert all("product_id" in hit and 0 <= hit["score"] <= 1 for hit in hits)
    policy_hits = context.container.vector_store.search_policies(
        "demo-store", "سياسة الاسترجاع", top_k=3
    )
    assert any(hit["source_ref"] == "policy:returns-ar-v1" for hit in policy_hits)


def test_repository_updates_live_price_and_prevents_duplicate_id(context: TestContext) -> None:
    with context.session_factory.begin() as session:
        repository = ProductRepository(session)
        updated = repository.update(
            "demo-store",
            "A101",
            ProductUpdateInput(price=Decimal("1301.00")),
            mark_reviewed=False,
        )
        assert updated.price == Decimal("1301.00")
    with context.session_factory.begin() as session:
        repository = ProductRepository(session)
        record = repository.get("demo-store", "A101")
        with pytest.raises(ConflictError):
            repository.add(record)
