"""Marketing generation, editing, and server-side approval."""

from decimal import Decimal

from fastapi import APIRouter, status

from app.api.dependencies import ContainerDependency, CurrentUser, DatabaseDependency, MarketerUser
from app.application.approve_and_publish import MarketingLifecycleUseCase, PublisherSet
from app.application.generate_marketing_pack import GenerateMarketingPackUseCase
from app.domain.models import MarketingPack, MarketingPackUpdateInput
from app.repositories.audit_repository import AuditRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publication_repository import PublicationRepository
from app.services.ai_usage import record_ai_operation
from app.services.billing import check_and_increment, require_feature
from app.services.marketing import MarketingService

router = APIRouter(tags=["marketing"])


def _lifecycle(db: DatabaseDependency, container: ContainerDependency) -> MarketingLifecycleUseCase:
    return MarketingLifecycleUseCase(
        ContentRepository(db),
        PublicationRepository(db),
        AuditRepository(db),
        MarketingService(container.ai_provider),
        PublisherSet(container.facebook_publisher, container.instagram_publisher),
    )


@router.post(
    "/products/{product_id}/marketing-packs",
    response_model=MarketingPack,
    status_code=status.HTTP_201_CREATED,
)
def generate_pack(
    product_id: str,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MarketingPack:
    require_feature(db, user.store_id, "content_studio")
    check_and_increment(db, user.store_id, "ai_operations")
    check_and_increment(db, user.store_id, "posts")
    use_case = GenerateMarketingPackUseCase(
        ProductRepository(db),
        ContentRepository(db),
        MarketingService(container.ai_provider),
    )
    result = use_case.execute(user.store_id, product_id)
    record_ai_operation(
        db,
        user.store_id,
        "marketing_pack_generate",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=Decimal("0") if container.settings.ai_provider == "deterministic" else None,
    )
    return result


@router.get("/marketing-packs/{pack_id}", response_model=MarketingPack)
def get_pack(pack_id: int, user: CurrentUser, db: DatabaseDependency) -> MarketingPack:
    require_feature(db, user.store_id, "content_studio")
    return ContentRepository(db).get(pack_id, user.store_id)


@router.patch("/marketing-packs/{pack_id}", response_model=MarketingPack)
def update_pack(
    pack_id: int,
    changes: MarketingPackUpdateInput,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MarketingPack:
    require_feature(db, user.store_id, "content_studio")
    return _lifecycle(db, container).update(user.store_id, pack_id, changes)


@router.post("/marketing-packs/{pack_id}/approve", response_model=MarketingPack)
def approve_pack(
    pack_id: int,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MarketingPack:
    require_feature(db, user.store_id, "content_studio")
    return _lifecycle(db, container).approve(user.store_id, pack_id, user.email)

