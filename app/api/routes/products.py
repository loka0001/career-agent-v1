"""Product onboarding, review, and activation endpoints."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import ContainerDependency, CurrentUser, DatabaseDependency, MarketerUser
from app.application.onboard_product import OnboardProductUseCase
from app.application.product_management import ProductManagementUseCase
from app.domain.errors import InvalidInputError
from app.domain.models import (
    InventoryAdjustmentInput,
    InventoryTransactionOut,
    ProductCreateInput,
    ProductRecord,
    ProductUpdateInput,
    ProductVariantInput,
    ProductVariantOut,
)
from app.repositories.product_repository import ProductRepository
from app.services.ai_usage import record_ai_operation
from app.services.billing import check_and_increment, require_feature
from app.services.product_intelligence import ProductIntelligenceService
from app.services.inventory import (
    add_variant,
    adjust_inventory,
    list_inventory_transactions,
    list_variants,
)
from app.services.search_index import SearchIndexService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRecord])
def list_products(user: CurrentUser, db: DatabaseDependency) -> list[ProductRecord]:
    require_feature(db, user.store_id, "catalog")
    return ProductRepository(db).list(user.store_id)


@router.post(
    "/onboard",
    response_model=ProductRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and analyze a product image",
)
async def onboard_product(
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
    product_id: Annotated[str, Form(min_length=1, max_length=64)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
    category: Annotated[str, Form(min_length=1, max_length=100)],
    price: Annotated[Decimal, Form(gt=0)],
    stock: Annotated[int, Form(ge=0)],
    image: Annotated[UploadFile, File()],
    raw_features: Annotated[str, Form()] = "[]",
) -> ProductRecord:
    require_feature(db, user.store_id, "catalog")
    try:
        parsed_features = json.loads(raw_features)
        if not isinstance(parsed_features, list) or not all(
            isinstance(item, str) for item in parsed_features
        ):
            raise ValueError
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidInputError(
            "raw_features must be a JSON array of strings",
            details={"field": "raw_features"},
        ) from exc
    content = await image.read(container.settings.max_image_bytes + 1)
    container.malware_scanner.scan(content)
    product = ProductCreateInput(
        product_id=product_id,
        name=name,
        category=category,
        price=price,
        stock=stock,
        raw_features=parsed_features,
    )
    use_case = OnboardProductUseCase(
        ProductRepository(db),
        ProductIntelligenceService(container.ai_provider),
        container.image_storage,
        SearchIndexService(container.vector_store),
        max_image_bytes=container.settings.max_image_bytes,
    )
    check_and_increment(db, user.store_id, "ai_operations", amount=2)
    result = use_case.execute(
        store_id=user.store_id,
        product=product,
        filename=image.filename,
        content_type=image.content_type,
        image=content,
    )
    record_ai_operation(
        db,
        user.store_id,
        "product_onboard",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=Decimal("0") if container.settings.ai_provider == "deterministic" else None,
    )
    return result


@router.get("/{product_id}", response_model=ProductRecord)
def get_product(product_id: str, user: CurrentUser, db: DatabaseDependency) -> ProductRecord:
    require_feature(db, user.store_id, "catalog")
    return ProductRepository(db).get(user.store_id, product_id)


@router.patch("/{product_id}", response_model=ProductRecord)
def review_product(
    product_id: str,
    changes: ProductUpdateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProductRecord:
    require_feature(db, user.store_id, "catalog")
    use_case = ProductManagementUseCase(
        ProductRepository(db), SearchIndexService(container.vector_store)
    )
    return use_case.review(user.store_id, product_id, changes)


@router.post("/{product_id}/activate", response_model=ProductRecord)
def activate_product(
    product_id: str,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProductRecord:
    require_feature(db, user.store_id, "catalog")
    use_case = ProductManagementUseCase(
        ProductRepository(db), SearchIndexService(container.vector_store)
    )
    return use_case.activate(user.store_id, product_id)


@router.get("/{product_id}/variants", response_model=list[ProductVariantOut])
def product_variants(
    product_id: str, user: CurrentUser, db: DatabaseDependency
) -> list[ProductVariantOut]:
    require_feature(db, user.store_id, "catalog")
    return list_variants(db, user.store_id, product_id)


@router.post(
    "/{product_id}/variants", response_model=ProductVariantOut, status_code=status.HTTP_201_CREATED
)
def create_product_variant(
    product_id: str,
    payload: ProductVariantInput,
    user: MarketerUser,
    db: DatabaseDependency,
) -> ProductVariantOut:
    require_feature(db, user.store_id, "catalog")
    return add_variant(db, user.store_id, product_id, payload, actor_user_id=user.user_id)


@router.post("/{product_id}/inventory/adjust", response_model=InventoryTransactionOut)
def change_inventory(
    product_id: str,
    payload: InventoryAdjustmentInput,
    user: MarketerUser,
    db: DatabaseDependency,
) -> InventoryTransactionOut:
    require_feature(db, user.store_id, "catalog")
    return adjust_inventory(
        db,
        store_id=user.store_id,
        product_id=product_id,
        variant_id=payload.variant_id,
        delta=payload.delta,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
        allow_negative=payload.allow_negative,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        actor_user_id=user.user_id,
        require_local=True,
    )


@router.get("/{product_id}/inventory/transactions", response_model=list[InventoryTransactionOut])
def inventory_history(
    product_id: str,
    user: CurrentUser,
    db: DatabaseDependency,
) -> list[InventoryTransactionOut]:
    require_feature(db, user.store_id, "catalog")
    return list_inventory_transactions(db, user.store_id, product_id)
