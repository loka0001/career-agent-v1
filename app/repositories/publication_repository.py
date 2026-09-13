"""Publication attempts and idempotency records."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PublicationModel
from app.domain.enums import Platform, PublicationStatus
from app.domain.errors import NotFoundError
from app.domain.models import PublishResult


def to_publish_result(row: PublicationModel) -> PublishResult:
    return PublishResult(
        publication_id=row.id,
        platform=Platform(row.platform),
        success=row.status in {PublicationStatus.PUBLISHED.value, PublicationStatus.DEMO.value},
        external_id=row.external_id,
        permalink=row.permalink,
        error_code=row.error_code,
        error_message=row.error_message,
        raw_status=row.raw_status or row.status,
    )


class PublicationRepository:
    def __init__(self, session: Session):
        self._session = session

    def find_idempotent(
        self, pack_id: int, platform: Platform, request_id: str
    ) -> PublishResult | None:
        row = self._session.scalar(
            select(PublicationModel).where(
                PublicationModel.marketing_pack_id == pack_id,
                PublicationModel.platform == platform.value,
                PublicationModel.request_id == request_id,
            )
        )
        return to_publish_result(row) if row is not None else None

    def save(
        self,
        *,
        pack_id: int,
        request_id: str,
        result: PublishResult,
    ) -> PublishResult:
        status = PublicationStatus.FAILED
        if result.success and result.raw_status == "DEMO":
            status = PublicationStatus.DEMO
        elif result.success:
            status = PublicationStatus.PUBLISHED
        elif result.error_code == "publishing_disabled":
            status = PublicationStatus.DISABLED
        row = PublicationModel(
            marketing_pack_id=pack_id,
            platform=result.platform.value,
            status=status.value,
            external_id=result.external_id,
            permalink=result.permalink,
            error_code=result.error_code,
            error_message=result.error_message,
            raw_status=result.raw_status,
            request_id=request_id,
            completed_at=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.flush()
        return to_publish_result(row)

    def get(self, publication_id: int) -> PublishResult:
        row = self._session.get(PublicationModel, publication_id)
        if row is None:
            raise NotFoundError(details={"entity": "publication", "id": publication_id})
        return to_publish_result(row)

    def get_for_store(self, publication_id: int, store_id: str) -> PublishResult | None:
        row = self._session.scalar(
            select(PublicationModel).where(
                PublicationModel.id == publication_id,
                PublicationModel.marketing_pack.has(store_id=store_id),
            )
        )
        return to_publish_result(row) if row is not None else None
