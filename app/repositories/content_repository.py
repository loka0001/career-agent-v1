"""Marketing pack persistence, approval state, and invalidation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import MarketingPackModel, ProductModel
from app.domain.enums import MarketingStatus
from app.domain.errors import NotFoundError
from app.domain.models import MarketingPack, MarketingPackUpdateInput


def to_marketing_pack(row: MarketingPackModel) -> MarketingPack:
    return MarketingPack(
        id=row.id,
        product_id=row.product.product_id,
        facebook_message=row.facebook_message,
        instagram_caption=row.instagram_caption,
        hashtags=list(row.hashtags_json),
        image_url=row.image_url,
        validation_warnings=list(row.validation_warnings_json),
        version=row.version,
        status=MarketingStatus(row.status),
        approved_at=row.approved_at,
        approved_by=row.approved_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ContentRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_row(self, pack_id: int, store_id: str | None = None) -> MarketingPackModel:
        row = self._session.get(MarketingPackModel, pack_id)
        if row is None or (store_id is not None and row.store_id != store_id):
            raise NotFoundError(details={"entity": "marketing_pack", "id": pack_id})
        return row

    def get(self, pack_id: int, store_id: str | None = None) -> MarketingPack:
        return to_marketing_pack(self.get_row(pack_id, store_id))

    def create(
        self,
        *,
        store_id: str,
        product: ProductModel,
        facebook_message: str,
        instagram_caption: str,
        hashtags: list[str],
        image_url: str,
        warnings: list[str],
    ) -> MarketingPack:
        row = MarketingPackModel(
            store_id=store_id,
            product_pk=product.id,
            facebook_message=facebook_message,
            instagram_caption=instagram_caption,
            hashtags_json=hashtags,
            image_url=image_url,
            validation_warnings_json=warnings,
            version=1,
            status=MarketingStatus.DRAFT.value,
        )
        self._session.add(row)
        self._session.flush()
        return to_marketing_pack(row)

    def update(
        self,
        pack_id: int,
        changes: MarketingPackUpdateInput,
        warnings: list[str],
        store_id: str | None = None,
    ) -> MarketingPack:
        row = self.get_row(pack_id, store_id)
        for key, value in changes.model_dump(exclude_none=True).items():
            setattr(row, "hashtags_json" if key == "hashtags" else key, value)
        row.version += 1
        row.status = MarketingStatus.DRAFT.value
        row.validation_warnings_json = warnings
        row.approved_at = None
        row.approved_by = None
        row.approved_content_hash = None
        self._session.flush()
        return to_marketing_pack(row)

    def approve(
        self, pack_id: int, actor: str, content_hash: str, store_id: str | None = None
    ) -> MarketingPack:
        row = self.get_row(pack_id, store_id)
        row.status = MarketingStatus.APPROVED.value
        row.approved_at = datetime.now(UTC)
        row.approved_by = actor
        row.approved_content_hash = content_hash
        self._session.flush()
        return to_marketing_pack(row)

    def set_status(
        self, pack_id: int, status: MarketingStatus, store_id: str | None = None
    ) -> MarketingPack:
        row = self.get_row(pack_id, store_id)
        row.status = status.value
        self._session.flush()
        return to_marketing_pack(row)

    def product_for_pack(self, pack_id: int) -> ProductModel:
        row = self.get_row(pack_id)
        product = self._session.get(ProductModel, row.product_pk)
        if product is None:
            raise NotFoundError(details={"entity": "product"})
        return product
