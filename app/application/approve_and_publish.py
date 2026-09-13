"""Edit, validate, approve, and idempotently publish marketing content."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import MarketingStatus, Platform
from app.domain.errors import CommerceError, ConflictError, ContentNotApprovedError
from app.domain.models import MarketingPack, MarketingPackUpdateInput, PublishResult
from app.domain.validators import approved_content_hash
from app.integrations.facebook import FacebookPublisher
from app.integrations.instagram import InstagramPublisher
from app.repositories.audit_repository import AuditRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.product_repository import to_product_record
from app.repositories.publication_repository import PublicationRepository
from app.services.marketing import MarketingService


@dataclass(frozen=True)
class PublisherSet:
    facebook: FacebookPublisher
    instagram: InstagramPublisher


class MarketingLifecycleUseCase:
    def __init__(
        self,
        content: ContentRepository,
        publications: PublicationRepository,
        audit: AuditRepository,
        marketing: MarketingService,
        publishers: PublisherSet,
    ):
        self._content = content
        self._publications = publications
        self._audit = audit
        self._marketing = marketing
        self._publishers = publishers

    def update(
        self, store_id: str, pack_id: int, changes: MarketingPackUpdateInput
    ) -> MarketingPack:
        row = self._content.get_row(pack_id, store_id)
        product = to_product_record(row.product)
        facebook = changes.facebook_message or row.facebook_message
        instagram = changes.instagram_caption or row.instagram_caption
        warnings = self._marketing.validate(product, facebook, instagram)
        return self._content.update(pack_id, changes, warnings, store_id)

    def approve(self, store_id: str, pack_id: int, actor: str) -> MarketingPack:
        row = self._content.get_row(pack_id, store_id)
        if row.validation_warnings_json:
            raise ConflictError(
                "Critical validation warnings must be fixed before approval",
                details={"warnings": row.validation_warnings_json},
            )
        content_hash = approved_content_hash(
            row.facebook_message,
            row.instagram_caption,
            list(row.hashtags_json),
            row.version,
        )
        approved = self._content.approve(pack_id, actor, content_hash, store_id)
        self._audit.add(
            actor=actor,
            action="marketing_pack.approved",
            entity_type="marketing_pack",
            entity_id=str(pack_id),
            metadata={"version": row.version, "content_hash": content_hash},
            store_id=store_id,
        )
        return approved

    def publish(
        self,
        store_id: str,
        pack_id: int,
        platforms: list[Platform],
        request_id: str,
        actor: str,
    ) -> list[PublishResult]:
        row = self._content.get_row(pack_id, store_id)
        expected_hash = approved_content_hash(
            row.facebook_message,
            row.instagram_caption,
            list(row.hashtags_json),
            row.version,
        )
        approved_states = {
            MarketingStatus.APPROVED.value,
            MarketingStatus.PUBLISHED.value,
            MarketingStatus.PARTIAL.value,
            MarketingStatus.FAILED.value,
        }
        if row.status not in approved_states or row.approved_content_hash != expected_hash:
            raise ContentNotApprovedError()
        if not platforms:
            raise ConflictError("Select at least one publishing platform")

        results: list[PublishResult] = []
        for platform in dict.fromkeys(platforms):
            existing = self._publications.find_idempotent(pack_id, platform, request_id)
            if existing is not None:
                results.append(existing)
                continue
            try:
                if platform == Platform.FACEBOOK:
                    result = self._publishers.facebook.publish(row.image_url, row.facebook_message)
                else:
                    caption = row.instagram_caption
                    hashtags = " ".join(row.hashtags_json)
                    if hashtags and hashtags not in caption:
                        caption = f"{caption}\n\n{hashtags}"
                    result = self._publishers.instagram.publish(row.image_url, caption)
            except CommerceError as exc:
                result = PublishResult(
                    platform=platform,
                    success=False,
                    error_code=exc.code,
                    error_message=exc.public_message,
                    raw_status="ERROR",
                )
            saved = self._publications.save(pack_id=pack_id, request_id=request_id, result=result)
            results.append(saved)
            self._audit.add(
                actor=actor,
                action="marketing_pack.publish_attempt",
                entity_type="marketing_pack",
                entity_id=str(pack_id),
                metadata={
                    "platform": platform.value,
                    "success": saved.success,
                    "raw_status": saved.raw_status,
                },
                store_id=store_id,
            )

        successes = sum(result.success for result in results)
        if successes == len(results):
            status = MarketingStatus.PUBLISHED
        elif successes:
            status = MarketingStatus.PARTIAL
        else:
            status = MarketingStatus.FAILED
        self._content.set_status(pack_id, status, store_id)
        return results
