from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.enums import ProductStatus
from app.domain.errors import GroundingError, InvalidInputError
from app.domain.models import (
    CustomerNeed,
    ProductRecord,
    Recommendation,
    SalesAssistantResponse,
)
from app.domain.validators import (
    merge_features,
    validate_image_file,
    validate_marketing_content,
    validate_sales_response,
)


def product(product_id: str = "A900", price: str = "1000", stock: int = 4) -> ProductRecord:
    now = datetime.now(UTC)
    return ProductRecord(
        product_id=product_id,
        store_id="demo-store",
        name="Test Headphones",
        category="Audio",
        price=Decimal(price),
        stock=stock,
        features=["Bluetooth", "microphone"],
        customer_benefits=["مناسبة للمكالمات"],
        description="سماعة للمكالمات",
        image_summary="سماعة",
        original_image_url="/image.png",
        status=ProductStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_file_validation_checks_magic_mime_extension_and_size() -> None:
    png = b"\x89PNG\r\n\x1a\ncontent"
    assert validate_image_file("item.png", "image/png", png, max_bytes=100) == "image/png"
    with pytest.raises(InvalidInputError):
        validate_image_file("item.jpg", "image/png", png, max_bytes=100)
    with pytest.raises(InvalidInputError):
        validate_image_file("item.png", "image/png", b"not-png", max_bytes=100)
    with pytest.raises(InvalidInputError):
        validate_image_file("item.png", "image/png", png, max_bytes=8)


def test_feature_merge_normalizes_without_losing_first_spelling() -> None:
    assert merge_features(
        [" Bluetooth 5.3 ", "MICROPHONE"], ["bluetooth 5.3", " Comfortable "]
    ) == ["Bluetooth 5.3", "MICROPHONE", "Comfortable"]


def test_marketing_validator_rejects_wrong_price_and_unfounded_claims() -> None:
    warnings = validate_marketing_content(
        product(),
        "الأفضل الآن بسعر 900 جنيه مع خصم وبطارية 50 ساعة",
        "عرض خاص ومضمون 100%",
    )
    assert "price_mismatch:900!=1000" in warnings
    assert "unsupported_discount_or_scarcity_claim" in warnings
    assert "unsupported_absolute_claim" in warnings
    assert "unsupported_feature_claim:battery" in warnings
    assert "unsupported_feature_claim:technical_spec:50 ساعة" in warnings


def test_reply_validator_accepts_grounded_reply_and_rejects_wrong_price() -> None:
    item = product()
    need = CustomerNeed(intent="product_search", max_budget=Decimal("1200"))
    recommendation = Recommendation(
        product_id=item.product_id, score=1, reasons=["مطابق"], product=item
    )
    valid = SalesAssistantResponse(
        need=need,
        recommendations=[recommendation],
        reply="A900 بسعر 1000 جنيه",
        citations=["product:A900"],
        insufficient_context=False,
    )
    validate_sales_response(valid, {item.product_id: item}, {"product:A900"})
    invalid = valid.model_copy(update={"reply": "A900 بسعر 999 جنيه"})
    with pytest.raises(GroundingError):
        validate_sales_response(invalid, {item.product_id: item}, {"product:A900"})
    invented_feature = valid.model_copy(update={"reply": "A900 بسعر 1000 جنيه وبطارية 50 ساعة"})
    with pytest.raises(GroundingError):
        validate_sales_response(invented_feature, {item.product_id: item}, {"product:A900"})
