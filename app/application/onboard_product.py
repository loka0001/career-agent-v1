"""Product onboarding use case: validate, store, analyze, save, and index."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.enums import ProductStatus
from app.domain.models import ProductCreateInput, ProductRecord
from app.domain.validators import validate_image_file
from app.integrations.image_storage import ImageStorage
from app.repositories.product_repository import ProductRepository
from app.services.product_intelligence import ProductIntelligenceService
from app.services.search_index import SearchIndexService


class OnboardProductUseCase:
    def __init__(
        self,
        products: ProductRepository,
        intelligence: ProductIntelligenceService,
        image_storage: ImageStorage,
        search_index: SearchIndexService,
        *,
        max_image_bytes: int,
    ):
        self._products = products
        self._intelligence = intelligence
        self._image_storage = image_storage
        self._search_index = search_index
        self._max_image_bytes = max_image_bytes

    def execute(
        self,
        *,
        store_id: str,
        product: ProductCreateInput,
        filename: str | None,
        content_type: str | None,
        image: bytes,
    ) -> ProductRecord:
        mime_type = validate_image_file(
            filename,
            content_type,
            image,
            max_bytes=self._max_image_bytes,
        )
        stored = self._image_storage.store(image, mime_type, store_id=store_id)
        analysis, features, copy = self._intelligence.analyze(product, image, mime_type)
        now = datetime.now(UTC)
        record = ProductRecord(
            product_id=product.product_id,
            store_id=store_id,
            name=product.name.strip(),
            category=product.category.strip(),
            price=product.price,
            stock=product.stock,
            features=features,
            customer_benefits=copy.customer_benefits,
            description=copy.description,
            image_summary=analysis.image_summary,
            original_image_url=stored.original_url,
            public_image_url=stored.public_url,
            status=ProductStatus.DRAFT,
            created_at=now,
            updated_at=now,
            sku=product.sku or product.product_id,
            currency=product.currency.upper(),
            compare_at_price=product.compare_at_price,
            stock_policy=product.stock_policy,
            images=[stored.public_url or stored.original_url],
        )
        saved = self._products.add(record)
        self._search_index.index_product(saved)
        return saved
