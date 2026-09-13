"""Idempotent Meta publishing and publication lookup."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.api.dependencies import ContainerDependency, CurrentUser, DatabaseDependency, MarketerUser
from app.api.schemas import PublishRequest, PublishResponse
from app.application.approve_and_publish import MarketingLifecycleUseCase, PublisherSet
from app.domain.enums import Platform
from app.domain.errors import InvalidInputError, NotFoundError
from app.domain.models import PublishResult
from app.repositories.audit_repository import AuditRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.publication_repository import PublicationRepository
from app.services.billing import require_feature
from app.services.marketing import MarketingService
from app.services.meta_publishing import StoreMetaPublisher

router = APIRouter(tags=["publishing"])


@router.post("/marketing-packs/{pack_id}/publish", response_model=PublishResponse)
def publish_pack(
    pack_id: int,
    payload: PublishRequest,
    user: MarketerUser,
    container: ContainerDependency,
    db: DatabaseDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> PublishResponse:
    require_feature(db, user.store_id, "content_studio")
    if not idempotency_key.strip():
        raise InvalidInputError("Idempotency-Key is required")
    use_case = MarketingLifecycleUseCase(
        ContentRepository(db),
        PublicationRepository(db),
        AuditRepository(db),
        MarketingService(container.ai_provider),
        PublisherSet(
            (
                container.facebook_publisher
                if container.settings.demo_mode
                else StoreMetaPublisher(
                    db, container.settings, user.store_id, Platform.FACEBOOK
                )
            ),
            (
                container.instagram_publisher
                if container.settings.demo_mode
                else StoreMetaPublisher(
                    db, container.settings, user.store_id, Platform.INSTAGRAM
                )
            ),
        ),
    )
    results = use_case.publish(
        user.store_id, pack_id, payload.platforms, idempotency_key, user.email
    )
    return PublishResponse(results=results)


@router.get("/publications/{publication_id}", response_model=PublishResult)
def get_publication(
    publication_id: int, user: CurrentUser, db: DatabaseDependency
) -> PublishResult:
    require_feature(db, user.store_id, "content_studio")
    result = PublicationRepository(db).get_for_store(publication_id, user.store_id)
    if result is None:
        raise NotFoundError(details={"entity": "publication", "id": publication_id})
    return result

