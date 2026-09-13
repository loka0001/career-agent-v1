"""Multi-format content studio extending the grounded marketing service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import (
    ContentCampaignModel,
    ContentItemModel,
    ContentVersionModel,
    StoreBrandModel,
)
from app.domain.enums import Platform
from app.domain.errors import ConflictError, ContentNotApprovedError, NotFoundError
from app.domain.models import (
    BrandProfileInput,
    BrandProfileOut,
    CampaignGenerateInput,
    CampaignOut,
    ContentGenerateInput,
    ContentItemOut,
    ContentItemUpdateInput,
    ContentVersionOut,
)
from app.domain.validators import approval_snapshot_hash
from app.integrations.ai_provider import AIProvider
from app.integrations.facebook import FacebookPublisher
from app.integrations.instagram import InstagramPublisher
from app.repositories.audit_repository import AuditRepository
from app.repositories.product_repository import ProductRepository
from app.services.external_operations import (
    begin_external_operation,
    complete_external_operation,
    mark_external_operation_retryable,
)
from app.services.job_queue import enqueue_job, job_handler
from app.services.marketing import MarketingService
from app.services.meta_publishing import StoreMetaPublisher

_FACEBOOK: FacebookPublisher | None = None
_INSTAGRAM: InstagramPublisher | None = None
_AI_PROVIDER: AIProvider | None = None
_AI_PROVIDER_NAME = "deterministic"
_AI_MODEL = "deterministic"
_APP_SETTINGS: Settings | None = None


def configure_content_publishers(
    facebook: FacebookPublisher, instagram: InstagramPublisher
) -> None:
    global _FACEBOOK, _INSTAGRAM
    _FACEBOOK = facebook
    _INSTAGRAM = instagram


def configure_content_services(
    ai_provider: AIProvider,
    provider_name: str,
    model: str,
    settings: Settings,
) -> None:
    global _AI_MODEL, _AI_PROVIDER, _AI_PROVIDER_NAME, _APP_SETTINGS
    _AI_PROVIDER = ai_provider
    _AI_PROVIDER_NAME = provider_name
    _AI_MODEL = model
    _APP_SETTINGS = settings


def _brand_out(row: StoreBrandModel) -> BrandProfileOut:
    return BrandProfileOut(
        tone=row.tone,
        audience=row.audience,
        guidelines=row.guidelines,
        primary_color=row.primary_color,
        updated_at=row.updated_at,
    )


def get_brand(session: Session, store_id: str) -> BrandProfileOut:
    row = session.scalar(select(StoreBrandModel).where(StoreBrandModel.store_id == store_id))
    if row is None:
        row = StoreBrandModel(store_id=store_id)
        session.add(row)
        session.flush()
    return _brand_out(row)


def save_brand(session: Session, store_id: str, payload: BrandProfileInput) -> BrandProfileOut:
    row = session.scalar(select(StoreBrandModel).where(StoreBrandModel.store_id == store_id))
    if row is None:
        row = StoreBrandModel(store_id=store_id)
        session.add(row)
    row.tone = payload.tone
    row.audience = payload.audience
    row.guidelines = payload.guidelines
    row.primary_color = payload.primary_color
    session.flush()
    return _brand_out(row)


def _item_out(row: ContentItemModel) -> ContentItemOut:
    return ContentItemOut(
        id=row.id,
        campaign_id=row.campaign_id,
        product_id=row.product_id,
        content_format=row.content_format,
        platform=Platform(row.platform),
        tone=row.tone,
        title=row.title,
        body=row.body,
        caption=row.caption,
        hashtags=list(row.hashtags_json),
        cta=row.cta,
        validation_warnings=list(row.validation_warnings_json),
        status=row.status,
        current_version=row.current_version,
        scheduled_for=row.scheduled_for,
        published_at=row.published_at,
        external_id=row.external_id,
        approved_at=row.approved_at,
        approved_by=row.approved_by,
        approved_by_user_id=row.approved_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _snapshot(row: ContentItemModel) -> dict[str, Any]:
    return {
        "title": row.title,
        "body": row.body,
        "caption": row.caption,
        "hashtags": list(row.hashtags_json),
        "cta": row.cta,
        "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
    }


def _approval_snapshot(row: ContentItemModel) -> dict[str, Any]:
    return {
        **_snapshot(row),
        "product_id": row.product_id,
        "content_format": row.content_format,
        "platform": row.platform,
        "tone": row.tone,
        "current_version": row.current_version,
    }


def _current_approval_hash(row: ContentItemModel) -> str:
    return approval_snapshot_hash(_approval_snapshot(row))


def _invalidate_approval(row: ContentItemModel) -> None:
    row.approved_at = None
    row.approved_by = None
    row.approved_by_user_id = None
    row.approved_content_hash = None


def _publish_payload(row: ContentItemModel) -> dict[str, Any]:
    return {
        "content_item_id": row.id,
        "content_version": row.current_version,
        "approval_hash": row.approved_content_hash,
    }


def _save_version(session: Session, row: ContentItemModel, user_id: str | None) -> None:
    session.add(
        ContentVersionModel(
            content_item_id=row.id,
            version=row.current_version,
            snapshot_json=_snapshot(row),
            created_by_user_id=user_id,
        )
    )


def _format_body(content_format: str, name: str, benefits: list[str], cta: str) -> str:
    bullets = "\n".join(f"- {benefit}" for benefit in benefits)
    templates = {
        "sales_post": f"{name}\n{bullets}\n{cta}",
        "educational_post": f"كيف تختار {name}؟\n{bullets}\n{cta}",
        "story_sequence": (
            f"Story 1: هل تبحث عن حل عملي؟\nStory 2: {name}\nStory 3:\n{bullets}\nStory 4: {cta}"
        ),
        "carousel": f"Slide 1: {name}\nSlide 2-4:\n{bullets}\nLast slide: {cta}",
        "reel_script": f"Hook: {name}\nDemo:\n{bullets}\nClosing: {cta}",
        "limited_offer": f"عرض محدود على {name}\n{bullets}\n{cta}",
        "comparison": f"هل {name} مناسب لك؟\n{bullets}\n{cta}",
        "faq": f"أسئلة شائعة عن {name}\n{bullets}\n{cta}",
    }
    return templates[content_format]


def generate_content(
    session: Session,
    store_id: str,
    user_id: str | None,
    payload: ContentGenerateInput,
    marketing: MarketingService,
    *,
    campaign_id: int | None = None,
) -> ContentItemOut:
    product = ProductRepository(session).get(store_id, payload.product_id)
    brief, warnings = marketing.generate(product)
    brand = get_brand(session, store_id)
    tone = payload.tone or brand.tone
    body = _format_body(
        payload.content_format,
        product.name,
        brief.benefits,
        brief.call_to_action,
    )
    caption = (
        brief.facebook_message if payload.platform == Platform.FACEBOOK else brief.instagram_caption
    )
    row = ContentItemModel(
        store_id=store_id,
        campaign_id=campaign_id,
        product_id=product.product_id,
        content_format=payload.content_format,
        platform=payload.platform.value,
        tone=tone,
        title=brief.hook,
        body=body,
        caption=caption,
        hashtags_json=list(dict.fromkeys(brief.hashtags)),
        cta=brief.call_to_action,
        validation_warnings_json=warnings,
        status="draft",
        current_version=1,
        scheduled_for=payload.scheduled_for,
    )
    session.add(row)
    session.flush()
    _save_version(session, row, user_id)
    session.flush()
    return _item_out(row)


def list_content(session: Session, store_id: str) -> list[ContentItemOut]:
    rows = session.scalars(
        select(ContentItemModel)
        .where(ContentItemModel.store_id == store_id)
        .order_by(ContentItemModel.created_at.desc())
    ).all()
    return [_item_out(row) for row in rows]


def _row(session: Session, store_id: str, item_id: int) -> ContentItemModel:
    row = session.scalar(
        select(ContentItemModel).where(
            ContentItemModel.id == item_id,
            ContentItemModel.store_id == store_id,
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "content_item", "id": item_id})
    return row


def _require_editable_content(row: ContentItemModel) -> None:
    if row.status in {"published", "publishing", "publish_retrying", "publish_unknown"}:
        raise ConflictError(
            "Content delivery must be resolved before editing or approval",
            details={"status": row.status},
        )


def update_content(
    session: Session,
    store_id: str,
    item_id: int,
    payload: ContentItemUpdateInput,
    user_id: str,
    marketing: MarketingService,
) -> ContentItemOut:
    row = _row(session, store_id, item_id)
    _require_editable_content(row)
    for field in ("title", "body", "caption", "cta", "scheduled_for"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)
    if payload.hashtags is not None:
        row.hashtags_json = list(dict.fromkeys(payload.hashtags))
    product = ProductRepository(session).get(store_id, row.product_id)
    row.validation_warnings_json = marketing.validate(product, row.caption, row.caption)
    row.status = "draft"
    _invalidate_approval(row)
    row.current_version += 1
    session.flush()
    _save_version(session, row, user_id)
    return _item_out(row)


def regenerate_section(
    session: Session,
    store_id: str,
    item_id: int,
    section: str,
    user_id: str,
    marketing: MarketingService,
) -> ContentItemOut:
    row = _row(session, store_id, item_id)
    _require_editable_content(row)
    product = ProductRepository(session).get(store_id, row.product_id)
    brief, _ = marketing.generate(product)
    replacements: dict[str, Any] = {
        "title": brief.hook,
        "body": _format_body(
            row.content_format,
            product.name,
            brief.benefits,
            brief.call_to_action,
        ),
        "caption": (
            brief.facebook_message
            if row.platform == Platform.FACEBOOK.value
            else brief.instagram_caption
        ),
        "hashtags": brief.hashtags,
        "cta": brief.call_to_action,
    }
    update = ContentItemUpdateInput(
        **{("hashtags" if section == "hashtags" else section): replacements[section]}
    )
    return update_content(session, store_id, item_id, update, user_id, marketing)


def approve_content(
    session: Session,
    store_id: str,
    item_id: int,
    *,
    actor_user_id: str,
    actor: str,
) -> ContentItemOut:
    row = _row(session, store_id, item_id)
    _require_editable_content(row)
    if row.validation_warnings_json:
        raise ConflictError(
            "Content has factual validation warnings",
            details={"warnings": row.validation_warnings_json},
        )
    row.status = "approved"
    row.approved_at = datetime.now(UTC)
    row.approved_by = actor
    row.approved_by_user_id = actor_user_id
    row.approved_content_hash = _current_approval_hash(row)
    session.flush()
    AuditRepository(session).add(
        actor=actor,
        actor_user_id=actor_user_id,
        action="content_item.approved",
        entity_type="content_item",
        entity_id=str(row.id),
        metadata={
            "version": row.current_version,
            "content_hash": row.approved_content_hash,
        },
        store_id=store_id,
    )
    if row.scheduled_for is not None:
        enqueue_job(
            session,
            job_type="content.publish",
            store_id=store_id,
            payload=_publish_payload(row),
            run_at=row.scheduled_for,
            dedup_key=f"content-publish:{row.id}:{row.current_version}",
        )
        row.status = "scheduled"
    return _item_out(row)


def queue_approved_content(session: Session, store_id: str, item_id: int) -> ContentItemOut:
    row = _row(session, store_id, item_id)
    if (
        row.status not in {"approved", "scheduled"}
        or row.approved_at is None
        or row.approved_by_user_id is None
        or row.approved_content_hash is None
        or row.approved_content_hash != _current_approval_hash(row)
    ):
        raise ContentNotApprovedError()
    enqueue_job(
        session,
        job_type="content.publish",
        store_id=store_id,
        payload=_publish_payload(row),
        run_at=row.scheduled_for if row.status == "scheduled" else None,
        dedup_key=f"content-publish:{row.id}:{row.current_version}",
    )
    return _item_out(row)


def versions(session: Session, store_id: str, item_id: int) -> list[ContentVersionOut]:
    _row(session, store_id, item_id)
    rows = session.scalars(
        select(ContentVersionModel)
        .where(ContentVersionModel.content_item_id == item_id)
        .order_by(ContentVersionModel.version.desc())
    ).all()
    return [
        ContentVersionOut(
            version=row.version,
            snapshot=dict(row.snapshot_json),
            created_by_user_id=row.created_by_user_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _campaign_out(row: ContentCampaignModel) -> CampaignOut:
    return CampaignOut(
        id=row.id,
        name=row.name,
        goal=row.goal,
        budget=row.budget_numeric,
        product_ids=list(row.product_ids_json),
        concept=row.concept,
        audience=row.audience,
        offer=row.offer,
        landing_copy=row.landing_copy,
        whatsapp_template=row.whatsapp_template,
        kpis=list(row.kpis_json),
        status=row.status,
        created_at=row.created_at,
    )


def generate_campaign(
    session: Session,
    store_id: str,
    user_id: str,
    payload: CampaignGenerateInput,
    marketing: MarketingService,
) -> CampaignOut:
    products = [
        ProductRepository(session).get(store_id, product_id) for product_id in payload.product_ids
    ]
    names = "، ".join(product.name for product in products)
    audience = payload.audience or get_brand(session, store_id).audience
    offer = payload.offer or "اختيار مناسب حسب احتياج العميل"
    row = ContentCampaignModel(
        store_id=store_id,
        name=payload.name,
        goal=payload.goal,
        budget_numeric=payload.budget,
        product_ids_json=payload.product_ids,
        concept=f"{payload.goal}: إبراز القيمة العملية لمنتجات {names}",
        audience=audience,
        offer=offer,
        landing_copy=f"اكتشف {names}. {offer}. تواصل معنا لاختيار الأنسب.",
        whatsapp_template=f"أهلًا {{{{name}}}}، جهزنا لك اختيارات من {names}.",
        kpis_json=["conversations", "checkout_started", "orders", "revenue"],
        status="draft",
    )
    session.add(row)
    session.flush()
    for product in products:
        generate_content(
            session,
            store_id,
            user_id,
            ContentGenerateInput(
                product_id=product.product_id,
                content_format="sales_post",
                platform=Platform.FACEBOOK,
            ),
            marketing,
            campaign_id=row.id,
        )
    return _campaign_out(row)


@job_handler("content.generate_automation")
def generate_automation_content_job(session: Session, payload: dict[str, Any]) -> None:
    from app.services.ai_usage import record_ai_operation
    from app.services.billing import check_and_increment

    run_id = int(payload["run_id"])
    existing = session.scalar(
        select(ContentItemModel.id).where(
            ContentItemModel.store_id == str(payload["store_id"]),
            ContentItemModel.title.like(f"%[automation:{run_id}]%"),
        )
    )
    if existing is not None:
        return
    if _AI_PROVIDER is None:
        raise ConflictError("Content AI provider is not configured")
    store_id = str(payload["store_id"])
    check_and_increment(session, store_id, "ai_operations")
    check_and_increment(session, store_id, "posts")
    item = generate_content(
        session,
        store_id,
        None,
        ContentGenerateInput(
            product_id=str(payload["product_id"]),
            content_format=str(payload.get("content_format", "sales_post")),
            platform=Platform(str(payload.get("platform", "facebook"))),
            tone=str(payload.get("tone", "")),
        ),
        MarketingService(_AI_PROVIDER),
    )
    row = session.get(ContentItemModel, item.id)
    if row is not None:
        row.title = f"{row.title} [automation:{run_id}]"
    record_ai_operation(
        session,
        store_id,
        "automation_content_generate",
        _AI_PROVIDER_NAME,
        _AI_MODEL,
        ai_provider=_AI_PROVIDER,
    )


@job_handler("content.publish")
def publish_content_job(session: Session, payload: dict[str, Any]) -> None:
    item = session.get(ContentItemModel, int(payload["content_item_id"]))
    if item is None or item.status == "published":
        return
    payload_version = int(payload.get("content_version", 0))
    payload_hash = str(payload.get("approval_hash", ""))
    if payload_version != item.current_version or payload_hash != item.approved_content_hash:
        return
    if item.status not in {"approved", "scheduled", "publishing", "publish_retrying"}:
        raise ContentNotApprovedError()
    if not payload_hash or payload_hash != _current_approval_hash(item):
        raise ContentNotApprovedError()
    product = ProductRepository(session).get(item.store_id, item.product_id)
    image_url = product.public_image_url or product.original_image_url
    platform = Platform(item.platform)
    publisher: FacebookPublisher | InstagramPublisher | StoreMetaPublisher | None
    if _APP_SETTINGS is not None and not _APP_SETTINGS.demo_mode:
        publisher = StoreMetaPublisher(
            session,
            _APP_SETTINGS,
            item.store_id,
            platform,
        )
    else:
        publisher = _FACEBOOK if platform == Platform.FACEBOOK else _INSTAGRAM
    if publisher is None:
        raise ConflictError("Content publisher is not configured")
    operation_key = f"content-item:{item.id}:{payload_version}"
    original_status = item.status
    item.status = "publishing"
    decision = begin_external_operation(
        session,
        store_id=item.store_id,
        operation_key=operation_key,
        operation_type="content.publish",
        entity_type="content_item",
        entity_id=str(item.id),
    )
    if decision.requires_reconciliation:
        item.status = "publish_unknown"
        AuditRepository(session).add(
            actor="system",
            actor_user_id=item.approved_by_user_id,
            action="content_item.publish_unknown",
            entity_type="content_item",
            entity_id=str(item.id),
            metadata={
                "platform": item.platform,
                "attempt_id": decision.attempt_id,
                "operation_key": operation_key,
                "manual_review_required": True,
            },
            store_id=item.store_id,
        )
        return
    if not decision.should_execute:
        item.status = "published"
        item.external_id = decision.external_id
        item.published_at = datetime.now(UTC)
        return
    result = publisher.publish(image_url, item.caption)
    if not result.success:
        mark_external_operation_retryable(
            session,
            item.store_id,
            operation_key,
            result.error_code,
        )
        item.status = "publish_retrying" if original_status != "scheduled" else "scheduled"
        session.commit()
        raise ConflictError(
            "Content publishing failed",
            details={"error_code": result.error_code},
        )
    complete_external_operation(
        session,
        item.store_id,
        operation_key,
        external_id=result.external_id,
    )
    item.status = "published"
    item.external_id = result.external_id
    item.published_at = datetime.now(UTC)
    AuditRepository(session).add(
        actor="system",
        actor_user_id=item.approved_by_user_id,
        action="content_item.published",
        entity_type="content_item",
        entity_id=str(item.id),
        metadata={
            "platform": item.platform,
            "external_id": item.external_id,
            "approval_hash": item.approved_content_hash,
        },
        store_id=item.store_id,
    )
