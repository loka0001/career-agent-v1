"""Plan catalog, subscription state, and enforced monthly usage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    AutomationModel,
    ChannelModel,
    MembershipModel,
    OrganizationModel,
    PlanModel,
    StoreModel,
    StripeEventModel,
    SubscriptionModel,
    UsageRecordModel,
    UserModel,
)
from app.domain.errors import ConflictError, NotFoundError, QuotaExceededError
from app.domain.models import CheckoutLink, PlanOut, SubscriptionOut
from app.integrations.billing import BillingProvider
from app.integrations.stripe_api import StripeEvent


class PlanDefinition(TypedDict):
    name: str
    price: Decimal
    quotas: dict[str, int]
    features: list[str]


PLAN_DEFINITIONS: dict[str, PlanDefinition] = {
    "starter": {
        "name": "Starter",
        "price": Decimal("499.00"),
        "quotas": {
            "conversations": 500,
            "channels": 2,
            "team_members": 2,
            "ai_operations": 200,
            "posts": 30,
            "automations": 3,
        },
        "features": ["inbox", "catalog", "content_studio", "website_widget"],
    },
    "growth": {
        "name": "Growth",
        "price": Decimal("1499.00"),
        "quotas": {
            "conversations": 5000,
            "channels": 10,
            "team_members": 10,
            "ai_operations": 3000,
            "posts": 300,
            "automations": 30,
        },
        "features": [
            "inbox",
            "catalog",
            "content_studio",
            "website_widget",
            "opportunities",
            "analytics",
            "automations",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": Decimal("3999.00"),
        "quotas": {
            "conversations": -1,
            "channels": -1,
            "team_members": -1,
            "ai_operations": 20000,
            "posts": 2000,
            "automations": -1,
        },
        "features": [
            "inbox",
            "catalog",
            "content_studio",
            "website_widget",
            "opportunities",
            "analytics",
            "automations",
            "priority_support",
            "advanced_integrations",
        ],
    },
}
INTERNAL_TRIAL_DAYS = 14
USABLE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def channel_family(channel_type: str) -> str:
    if channel_type in {"messenger", "facebook_comments"}:
        return "facebook"
    if channel_type in {"instagram_dm", "instagram_comments"}:
        return "instagram"
    return channel_type


def organization_channel_count(session: Session, organization_id: str | None) -> int:
    channel_types = session.scalars(
        select(ChannelModel.channel_type)
        .join(StoreModel, StoreModel.id == ChannelModel.store_id)
        .where(StoreModel.organization_id == organization_id)
    ).all()
    return len({channel_family(value) for value in channel_types})


def _period() -> tuple[datetime, datetime, str]:
    now = datetime.now(UTC)
    start = datetime(now.year, now.month, 1, tzinfo=UTC)
    end = (
        datetime(now.year + 1, 1, 1, tzinfo=UTC)
        if now.month == 12
        else datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    )
    return start, end, f"{now.year:04d}-{now.month:02d}"


def ensure_plans(session: Session) -> None:
    for key, definition in PLAN_DEFINITIONS.items():
        row = session.get(PlanModel, key)
        if row is None:
            session.add(
                PlanModel(
                    key=key,
                    name=str(definition["name"]),
                    price_numeric=definition["price"],
                    quotas_json=dict(definition["quotas"]),
                    features_json=list(definition["features"]),
                    is_active=True,
                )
            )
    session.flush()


def _plan_out(row: PlanModel) -> PlanOut:
    return PlanOut(
        key=row.key,
        name=row.name,
        price=row.price_numeric,
        quotas={key: int(value) for key, value in row.quotas_json.items()},
        features=list(row.features_json),
    )


def list_plans(session: Session) -> list[PlanOut]:
    ensure_plans(session)
    return [_plan_out(row) for row in session.scalars(select(PlanModel)).all()]


def _is_free_access_subscription(subscription: SubscriptionModel) -> bool:
    return (
        subscription.plan_key == "growth"
        and subscription.status == "active"
        and subscription.provider == "internal"
        and subscription.trial_end is None
    )


def ensure_subscription(
    session: Session,
    organization_id: str,
    *,
    free_access: bool = False,
) -> SubscriptionModel:
    ensure_plans(session)
    row = session.scalar(
        select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
    )
    if row is not None:
        if free_access and not _is_free_access_subscription(row):
            organization = session.get(OrganizationModel, organization_id)
            if organization is None:
                raise NotFoundError(details={"entity": "organization"})
            now = datetime.now(UTC)
            organization.plan = "growth"
            row.plan_key = "growth"
            row.status = "active"
            row.provider = "internal"
            row.provider_customer_id = None
            row.provider_subscription_id = None
            row.trial_end = None
            row.current_period_start = now
            row.current_period_end = now + timedelta(days=31)
            row.cancel_at_period_end = False
            session.flush()
        return row
    organization = session.get(OrganizationModel, organization_id)
    if organization is None:
        raise NotFoundError(details={"entity": "organization"})
    start = datetime.now(UTC)
    end = start + timedelta(days=31 if free_access else INTERNAL_TRIAL_DAYS)
    plan_key = "growth"
    organization.plan = plan_key
    row = SubscriptionModel(
        organization_id=organization_id,
        plan_key=plan_key,
        status="active" if free_access else "trialing",
        provider="internal",
        trial_end=None if free_access else end,
        current_period_start=start,
        current_period_end=end,
    )
    session.add(row)
    session.flush()
    return row


def subscription_out(
    session: Session,
    organization_id: str,
    *,
    free_access: bool = False,
) -> SubscriptionOut:
    subscription = ensure_subscription(session, organization_id, free_access=free_access)
    plan = session.get(PlanModel, subscription.plan_key)
    if plan is None:
        raise NotFoundError(details={"entity": "plan"})
    _, _, period_key = _period()
    rows = session.scalars(
        select(UsageRecordModel).where(
            UsageRecordModel.organization_id == organization_id,
            UsageRecordModel.period_key == period_key,
        )
    ).all()
    usage: dict[str, int] = {}
    for row in rows:
        usage[row.metric] = usage.get(row.metric, 0) + row.quantity
    usage["channels"] = organization_channel_count(session, organization_id)
    usage["automations"] = int(
        session.scalar(
            select(func.count(AutomationModel.id))
            .join(StoreModel, StoreModel.id == AutomationModel.store_id)
            .where(StoreModel.organization_id == organization_id)
        )
        or 0
    )
    usage["team_members"] = int(
        session.scalar(
            select(func.count(MembershipModel.id)).where(
                MembershipModel.organization_id == organization_id
            )
        )
        or 0
    )
    return SubscriptionOut(
        plan=_plan_out(plan),
        status=subscription.status,
        provider=subscription.provider,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        trial_end=subscription.trial_end,
        usage=usage,
    )


def _assert_subscription_usable(subscription: SubscriptionModel) -> None:
    now = datetime.now(UTC)
    trial_end = subscription.trial_end
    if trial_end is not None and trial_end.tzinfo is None:
        trial_end = trial_end.replace(tzinfo=UTC)
    trial_expired = subscription.status == "trialing" and (trial_end is None or trial_end <= now)
    if subscription.status not in USABLE_SUBSCRIPTION_STATUSES or trial_expired:
        raise QuotaExceededError(
            "An active subscription or trial is required",
            details={
                "subscription_status": subscription.status,
                "billing_action_required": True,
                "trial_expired": trial_expired,
            },
        )


def _locked_subscription(session: Session, organization_id: str) -> SubscriptionModel:
    row = ensure_subscription(session, organization_id)
    session.execute(
        update(SubscriptionModel)
        .where(SubscriptionModel.id == row.id)
        .values(updated_at=datetime.now(UTC))
    )
    subscription = session.scalar(
        select(SubscriptionModel)
        .where(SubscriptionModel.organization_id == organization_id)
        .with_for_update()
    )
    if subscription is None:
        raise NotFoundError(details={"entity": "subscription"})
    return subscription


def require_feature(session: Session, store_id: str, feature: str) -> None:
    """Enforce plan capabilities on the server, independent of UI visibility."""

    store = session.get(StoreModel, store_id)
    if store is None or store.organization_id is None:
        raise NotFoundError(details={"entity": "store"})
    subscription = ensure_subscription(session, store.organization_id)
    _assert_subscription_usable(subscription)
    plan = session.get(PlanModel, subscription.plan_key)
    if plan is None:
        raise NotFoundError(details={"entity": "plan"})
    if feature not in plan.features_json:
        raise QuotaExceededError(
            "This feature is not included in the current plan",
            details={
                "feature": feature,
                "plan": plan.key,
                "upgrade_required": True,
            },
        )


def check_and_increment(session: Session, store_id: str, metric: str, amount: int = 1) -> int:
    if amount < 1:
        return 0
    if metric == "ai_operations":
        from app.services.ai_usage import check_ai_budget

        check_ai_budget(session, store_id)
    store = session.get(StoreModel, store_id)
    if store is None or store.organization_id is None:
        raise NotFoundError(details={"entity": "store"})
    subscription = _locked_subscription(session, store.organization_id)
    _assert_subscription_usable(subscription)
    plan = session.get(PlanModel, subscription.plan_key)
    if plan is None:
        raise NotFoundError(details={"entity": "plan"})
    limit = int(plan.quotas_json.get(metric, -1))
    _, _, period_key = _period()
    usage = session.scalar(
        select(UsageRecordModel).where(
            UsageRecordModel.organization_id == store.organization_id,
            UsageRecordModel.store_id == store_id,
            UsageRecordModel.metric == metric,
            UsageRecordModel.period_key == period_key,
        )
    )
    organization_total = int(
        session.scalar(
            select(func.coalesce(func.sum(UsageRecordModel.quantity), 0)).where(
                UsageRecordModel.organization_id == store.organization_id,
                UsageRecordModel.metric == metric,
                UsageRecordModel.period_key == period_key,
            )
        )
        or 0
    )
    if limit >= 0 and organization_total + amount > limit:
        raise QuotaExceededError(
            details={
                "metric": metric,
                "limit": limit,
                "used": organization_total,
                "plan": plan.key,
                "upgrade_required": True,
            }
        )
    if usage is None:
        usage = UsageRecordModel(
            organization_id=store.organization_id,
            store_id=store_id,
            metric=metric,
            period_key=period_key,
            quantity=0,
        )
        session.add(usage)
    usage.quantity += amount
    session.flush()
    return organization_total + amount


def check_resource_limit(
    session: Session,
    store_id: str,
    metric: str,
    current_quantity: int,
    amount: int = 1,
) -> None:
    store = session.get(StoreModel, store_id)
    if store is None or store.organization_id is None:
        raise NotFoundError(details={"entity": "store"})
    subscription = _locked_subscription(session, store.organization_id)
    _assert_subscription_usable(subscription)
    plan = session.get(PlanModel, subscription.plan_key)
    if plan is None:
        raise NotFoundError(details={"entity": "plan"})
    limit = int(plan.quotas_json.get(metric, -1))
    if limit >= 0 and current_quantity + amount > limit:
        raise QuotaExceededError(
            details={
                "metric": metric,
                "limit": limit,
                "used": current_quantity,
                "plan": plan.key,
                "upgrade_required": True,
            }
        )


def change_plan(
    session: Session,
    organization_id: str,
    plan_key: str,
    provider: BillingProvider,
) -> SubscriptionOut:
    ensure_plans(session)
    plan = session.get(PlanModel, plan_key)
    if plan is None or not plan.is_active:
        raise NotFoundError(details={"entity": "plan", "key": plan_key})
    subscription = ensure_subscription(session, organization_id)
    customer_id, subscription_id = provider.change_plan(organization_id, plan_key)
    subscription.plan_key = plan_key
    subscription.provider = provider.name
    subscription.provider_customer_id = customer_id
    subscription.provider_subscription_id = subscription_id
    subscription.status = "active"
    organization = session.get(OrganizationModel, organization_id)
    if organization is not None:
        organization.plan = plan_key
    session.flush()
    return subscription_out(session, organization_id)


def start_plan_change(
    session: Session,
    organization_id: str,
    plan_key: str,
    public_base_url: str,
    provider: BillingProvider,
) -> SubscriptionOut | CheckoutLink:
    ensure_plans(session)
    plan = session.get(PlanModel, plan_key)
    if plan is None or not plan.is_active:
        raise NotFoundError(details={"entity": "plan", "key": plan_key})
    if provider.name == "demo":
        return change_plan(session, organization_id, plan_key, provider)
    subscription = ensure_subscription(session, organization_id)
    email = session.scalar(
        select(UserModel.email)
        .join(MembershipModel, MembershipModel.user_id == UserModel.id)
        .where(MembershipModel.organization_id == organization_id)
        .order_by(
            MembershipModel.role.desc(),
            MembershipModel.created_at,
        )
        .limit(1)
    )
    return provider.create_checkout(
        organization_id,
        plan_key,
        subscription.provider_customer_id,
        email,
        public_base_url,
    )


def create_billing_portal(
    session: Session,
    organization_id: str,
    public_base_url: str,
    provider: BillingProvider,
) -> CheckoutLink:
    subscription = ensure_subscription(session, organization_id)
    if provider.name != "stripe" or not subscription.provider_customer_id:
        raise ConflictError("No Stripe customer is linked to this organization")
    return provider.create_portal(subscription.provider_customer_id, public_base_url)


def _claim_stripe_event(session: Session, scope: str, event: StripeEvent) -> bool:
    try:
        with session.begin_nested():
            session.add(
                StripeEventModel(
                    scope=scope,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    livemode=event.livemode,
                    account_id=event.account_id,
                )
            )
            session.flush()
    except IntegrityError:
        return False
    return True


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _unix_datetime(value: object) -> datetime | None:
    return datetime.fromtimestamp(value, tz=UTC) if isinstance(value, int) else None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _subscription_reference(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        identifier = value.get("id")
        return identifier if isinstance(identifier, str) else None
    return None


def _metadata(data: dict[str, object]) -> dict[str, object]:
    value = data.get("metadata")
    return dict(value) if isinstance(value, dict) else {}


def _price_id(data: dict[str, object]) -> str | None:
    items = data.get("items")
    if not isinstance(items, dict):
        return None
    rows = items.get("data")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    price = rows[0].get("price")
    if isinstance(price, str):
        return price
    return _string(price.get("id")) if isinstance(price, dict) else None


def _subscription_row_for_event(
    session: Session,
    data: dict[str, object],
) -> SubscriptionModel | None:
    metadata = _metadata(data)
    organization_id = _string(metadata.get("organization_id"))
    if organization_id:
        return session.scalar(
            select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        )
    subscription_id = _subscription_reference(data.get("subscription")) or _string(data.get("id"))
    if subscription_id:
        row = session.scalar(
            select(SubscriptionModel).where(
                SubscriptionModel.provider_subscription_id == subscription_id
            )
        )
        if row is not None:
            return row
    customer_id = _string(data.get("customer"))
    if customer_id:
        return session.scalar(
            select(SubscriptionModel).where(SubscriptionModel.provider_customer_id == customer_id)
        )
    return None


def _apply_subscription(
    session: Session,
    provider: BillingProvider,
    data: dict[str, object],
    event_time: datetime,
) -> None:
    metadata = _metadata(data)
    organization_id = _string(metadata.get("organization_id"))
    row = _subscription_row_for_event(session, data)
    if row is None and organization_id:
        row = ensure_subscription(session, organization_id)
    if row is None:
        raise NotFoundError(details={"entity": "subscription", "provider": "stripe"})
    if row.last_provider_event_at and event_time < _utc(row.last_provider_event_at):
        return
    plan_key = _string(metadata.get("plan_key"))
    if plan_key not in PLAN_DEFINITIONS:
        price_id = _price_id(data)
        plan_key = provider.plan_for_price(price_id) if price_id else None
    if plan_key in PLAN_DEFINITIONS:
        row.plan_key = plan_key
    row.provider = "stripe"
    row.provider_customer_id = _string(data.get("customer")) or row.provider_customer_id
    row.provider_subscription_id = _string(data.get("id")) or row.provider_subscription_id
    status = _string(data.get("status"))
    if status:
        row.status = status
    row.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
    row.trial_end = _unix_datetime(data.get("trial_end"))
    row.current_period_start = (
        _unix_datetime(data.get("current_period_start")) or row.current_period_start
    )
    row.current_period_end = (
        _unix_datetime(data.get("current_period_end")) or row.current_period_end
    )
    row.last_provider_event_at = event_time
    organization = session.get(OrganizationModel, row.organization_id)
    if organization is not None and plan_key in PLAN_DEFINITIONS:
        organization.plan = plan_key
    session.flush()


def handle_billing_webhook(
    session: Session,
    provider: BillingProvider,
    body: bytes,
    signature_header: str,
) -> bool:
    event = provider.verify_event(body, signature_header)
    if not _claim_stripe_event(session, "billing", event):
        return False
    event_time = datetime.fromtimestamp(event.created, tz=UTC)
    data: dict[str, object] = dict(event.data)
    if event.event_type == "checkout.session.completed":
        if data.get("mode") != "subscription":
            return True
        subscription_id = _subscription_reference(data.get("subscription"))
        if not subscription_id:
            raise ConflictError("Stripe Checkout did not create a subscription")
        subscription_data = provider.retrieve_subscription(subscription_id)
        checkout_metadata = _metadata(data)
        subscription_metadata = _metadata(subscription_data)
        for key in ("organization_id", "plan_key"):
            if key not in subscription_metadata and key in checkout_metadata:
                subscription_metadata[key] = checkout_metadata[key]
        subscription_data["metadata"] = subscription_metadata
        _apply_subscription(session, provider, subscription_data, event_time)
    elif event.event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        if event.event_type == "customer.subscription.deleted":
            data["status"] = "canceled"
        _apply_subscription(session, provider, data, event_time)
    elif event.event_type in {"invoice.payment_failed", "invoice.payment_action_required"}:
        row = _subscription_row_for_event(session, data)
        if row is not None and (
            row.last_provider_event_at is None or event_time >= _utc(row.last_provider_event_at)
        ):
            row.status = "past_due"
            row.last_provider_event_at = event_time
    elif event.event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        row = _subscription_row_for_event(session, data)
        if row is not None and (
            row.last_provider_event_at is None or event_time >= _utc(row.last_provider_event_at)
        ):
            row.status = "active"
            row.last_provider_event_at = event_time
    session.flush()
    return True
