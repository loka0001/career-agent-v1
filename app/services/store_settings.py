"""Persistent store profile and evidence-derived onboarding state."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AIUsageRecordModel,
    ApiKeyModel,
    AutomationModel,
    ConversationModel,
    ProductModel,
    ProviderConnectionModel,
    SalesQueryModel,
    StoreModel,
    StoreSettingsModel,
    UserModel,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import (
    AuthUser,
    OnboardingStatusOut,
    OnboardingStepOut,
    StoreSettingsInput,
    StoreSettingsOut,
)

DEFAULT_COLORS = {"primary": "#2563eb", "accent": "#14b8a6"}


def _ensure(session: Session, store_id: str) -> tuple[StoreModel, StoreSettingsModel]:
    store = session.get(StoreModel, store_id)
    if store is None:
        raise NotFoundError(details={"entity": "store"})
    settings = session.get(StoreSettingsModel, store_id)
    if settings is None:
        settings = StoreSettingsModel(store_id=store_id)
        session.add(settings)
        session.flush()
    return store, settings


def _store_evidence(
    session: Session, store: StoreModel, settings: StoreSettingsModel
) -> dict[str, bool]:
    product_count = int(
        session.scalar(select(func.count(ProductModel.id)).where(ProductModel.store_id == store.id))
        or 0
    )
    conversation_count = int(
        session.scalar(
            select(func.count(ConversationModel.id)).where(ConversationModel.store_id == store.id)
        )
        or 0
    )
    automation_count = int(
        session.scalar(
            select(func.count(AutomationModel.id)).where(AutomationModel.store_id == store.id)
        )
        or 0
    )
    connected = session.scalars(
        select(ProviderConnectionModel).where(
            ProviderConnectionModel.store_id == store.id,
            ProviderConnectionModel.status == "connected",
        )
    ).all()
    has_live_channel = any(
        row.connection_type in {"facebook_page", "instagram_business", "whatsapp_business"}
        for row in connected
    )
    has_widget = (
        session.scalar(
            select(ApiKeyModel.id).where(
                ApiKeyModel.store_id == store.id,
                ApiKeyModel.is_active.is_(True),
            )
        )
        is not None
    )
    has_assistant_test = (
        session.scalar(select(SalesQueryModel.id).where(SalesQueryModel.store_id == store.id))
        is not None
        or session.scalar(
            select(AIUsageRecordModel.id).where(AIUsageRecordModel.store_id == store.id)
        )
        is not None
    )
    return {
        "store": bool(store.name.strip() and settings.business_type.strip()),
        "brand": bool(settings.tone.strip() and settings.brand_colors_json),
        "products": product_count > 0,
        "channel": has_live_channel or has_widget,
        "policies": bool(settings.shipping_policy.strip() and settings.return_policy.strip()),
        "assistant": has_assistant_test,
        "conversation": conversation_count > 0,
        "automation": automation_count > 0,
    }


def _out(session: Session, store: StoreModel, settings: StoreSettingsModel) -> StoreSettingsOut:
    evidence = _store_evidence(session, store, settings)
    return StoreSettingsOut(
        store_id=store.id,
        slug=store.slug,
        store_name=store.name,
        default_language=store.default_language,
        business_type=settings.business_type,
        logo_url=settings.logo_url,
        brand_colors=dict(settings.brand_colors_json),
        tone=settings.tone,
        assistant_name=settings.assistant_name,
        assistant_instructions=settings.assistant_instructions,
        shipping_policy=settings.shipping_policy,
        return_policy=settings.return_policy,
        ai_monthly_budget=settings.ai_monthly_budget_numeric,
        onboarding_steps=evidence,
        onboarding_completed=all(evidence.values()),
        updated_at=settings.updated_at,
    )


def get_store_settings(session: Session, store_id: str) -> StoreSettingsOut:
    store, settings = _ensure(session, store_id)
    return _out(session, store, settings)


def save_store_settings(
    session: Session, store_id: str, payload: StoreSettingsInput
) -> StoreSettingsOut:
    store, settings = _ensure(session, store_id)
    store.name = payload.store_name
    store.default_language = payload.default_language.value
    settings.business_type = payload.business_type
    settings.logo_url = payload.logo_url
    settings.brand_colors_json = payload.brand_colors or DEFAULT_COLORS
    settings.tone = payload.tone
    settings.assistant_name = payload.assistant_name
    settings.assistant_instructions = payload.assistant_instructions
    settings.shipping_policy = payload.shipping_policy
    settings.return_policy = payload.return_policy
    settings.ai_monthly_budget_numeric = payload.ai_monthly_budget
    session.flush()
    return _out(session, store, settings)


def onboarding_status(session: Session, user: AuthUser) -> OnboardingStatusOut:
    store, settings = _ensure(session, user.store_id)
    evidence = _store_evidence(session, store, settings)
    user_row = session.get(UserModel, user.user_id)
    definitions = (
        (
            "account",
            "تأكيد الحساب",
            user_row is not None and user_row.email_verified_at is not None,
            "/app/security",
            "البريد الإلكتروني مؤكد",
        ),
        ("store", "بيانات المتجر", evidence["store"], "/app/settings", "الاسم والنشاط محفوظان"),
        ("brand", "هوية البراند", evidence["brand"], "/app/settings", "النبرة والألوان محفوظتان"),
        (
            "products",
            "كتالوج حقيقي",
            evidence["products"],
            "/app/products/new",
            "يوجد منتج واحد على الأقل",
        ),
        (
            "channel",
            "قناة بيع",
            evidence["channel"],
            "/app/integrations",
            "اتصال Live سليم أو مفتاح ويدجت نشط",
        ),
        (
            "policies",
            "سياسات التشغيل",
            evidence["policies"],
            "/app/settings",
            "سياسات الشحن والاسترجاع مكتملة",
        ),
        (
            "assistant",
            "اختبار المساعد",
            evidence["assistant"],
            "/app/agent-settings",
            "تم تسجيل استجابة فعلية",
        ),
        (
            "conversation",
            "صندوق الوارد",
            evidence["conversation"],
            "/app/inbox",
            "وصلت محادثة فعلية",
        ),
        (
            "automation",
            "أتمتة عملية",
            evidence["automation"],
            "/app/automations",
            "توجد قاعدة أتمتة محفوظة",
        ),
    )
    steps = [
        OnboardingStepOut(
            key=key,
            title=title,
            complete=complete,
            required=True,
            href=href,
            evidence=evidence_text,
        )
        for key, title, complete, href, evidence_text in definitions
    ]
    completed = sum(step.complete for step in steps)
    return OnboardingStatusOut(
        steps=steps,
        completed_count=completed,
        required_count=len(steps),
        ready_to_activate=completed == len(steps),
        activated=settings.onboarding_completed,
    )


def activate_store(session: Session, user: AuthUser) -> OnboardingStatusOut:
    status = onboarding_status(session, user)
    if not status.ready_to_activate:
        missing = [step.key for step in status.steps if step.required and not step.complete]
        raise ConflictError(
            "Onboarding evidence is incomplete",
            details={"missing_steps": missing},
        )
    settings = session.get(StoreSettingsModel, user.store_id)
    if settings is None:
        raise NotFoundError(details={"entity": "store_settings"})
    settings.onboarding_completed = True
    session.flush()
    return onboarding_status(session, user)
