"""Brand-aware content generation, campaigns, versions, approval, and scheduling."""

from decimal import Decimal

from fastapi import APIRouter, status

from app.api.dependencies import (
    ContainerDependency,
    CurrentUser,
    DatabaseDependency,
    MarketerUser,
)
from app.api.schemas import MessageResponse
from app.domain.models import (
    BrandProfileInput,
    BrandProfileOut,
    CampaignGenerateInput,
    CampaignOut,
    ContentGenerateInput,
    ContentItemOut,
    ContentItemUpdateInput,
    ContentRegenerateInput,
    ContentVersionOut,
)
from app.services.ai_usage import record_ai_operation
from app.services.billing import check_and_increment
from app.services.content_studio import (
    approve_content,
    generate_campaign,
    generate_content,
    get_brand,
    list_content,
    queue_approved_content,
    regenerate_section,
    save_brand,
    update_content,
    versions,
)
from app.services.marketing import MarketingService

router = APIRouter(prefix="/studio", tags=["content-studio"])


@router.get("/brand", response_model=BrandProfileOut)
def brand(user: CurrentUser, db: DatabaseDependency) -> BrandProfileOut:
    return get_brand(db, user.store_id)


@router.put("/brand", response_model=BrandProfileOut)
def update_brand(
    payload: BrandProfileInput,
    user: MarketerUser,
    db: DatabaseDependency,
) -> BrandProfileOut:
    return save_brand(db, user.store_id, payload)


@router.get("/content", response_model=list[ContentItemOut])
def content(user: CurrentUser, db: DatabaseDependency) -> list[ContentItemOut]:
    return list_content(db, user.store_id)


@router.post(
    "/content/generate",
    response_model=ContentItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_content(
    payload: ContentGenerateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ContentItemOut:
    check_and_increment(db, user.store_id, "ai_operations")
    check_and_increment(db, user.store_id, "posts")
    result = generate_content(
        db,
        user.store_id,
        user.user_id,
        payload,
        MarketingService(container.ai_provider),
    )
    record_ai_operation(
        db,
        user.store_id,
        "content_generate",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=(
            Decimal("0")
            if container.settings.ai_provider == "deterministic"
            else None
        ),
    )
    return result


@router.patch("/content/{item_id}", response_model=ContentItemOut)
def edit_content(
    item_id: int,
    payload: ContentItemUpdateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ContentItemOut:
    return update_content(
        db,
        user.store_id,
        item_id,
        payload,
        user.user_id,
        MarketingService(container.ai_provider),
    )


@router.post("/content/{item_id}/regenerate", response_model=ContentItemOut)
def regenerate(
    item_id: int,
    payload: ContentRegenerateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ContentItemOut:
    check_and_increment(db, user.store_id, "ai_operations")
    result = regenerate_section(
        db,
        user.store_id,
        item_id,
        payload.section,
        user.user_id,
        MarketingService(container.ai_provider),
    )
    record_ai_operation(
        db,
        user.store_id,
        "content_regenerate",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=(
            Decimal("0")
            if container.settings.ai_provider == "deterministic"
            else None
        ),
    )
    return result


@router.get(
    "/content/{item_id}/versions", response_model=list[ContentVersionOut]
)
def content_versions(
    item_id: int, user: CurrentUser, db: DatabaseDependency
) -> list[ContentVersionOut]:
    return versions(db, user.store_id, item_id)


@router.post("/content/{item_id}/approve", response_model=ContentItemOut)
def approve(
    item_id: int, user: MarketerUser, db: DatabaseDependency
) -> ContentItemOut:
    return approve_content(
        db,
        user.store_id,
        item_id,
        actor_user_id=user.user_id,
        actor=user.email,
    )


@router.post("/content/{item_id}/publish", response_model=MessageResponse)
def publish(
    item_id: int, user: MarketerUser, db: DatabaseDependency
) -> MessageResponse:
    queue_approved_content(db, user.store_id, item_id)
    return MessageResponse(message="content_publish_queued")


@router.post(
    "/campaigns/generate",
    response_model=CampaignOut,
    status_code=status.HTTP_201_CREATED,
)
def campaign(
    payload: CampaignGenerateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> CampaignOut:
    item_count = len(payload.product_ids)
    check_and_increment(db, user.store_id, "ai_operations", item_count)
    check_and_increment(db, user.store_id, "posts", item_count)
    result = generate_campaign(
        db,
        user.store_id,
        user.user_id,
        payload,
        MarketingService(container.ai_provider),
    )
    record_ai_operation(
        db,
        user.store_id,
        "campaign_generate",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=(
            Decimal("0")
            if container.settings.ai_provider == "deterministic"
            else None
        ),
    )
    return result
