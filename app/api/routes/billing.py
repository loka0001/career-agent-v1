"""Plan catalog, current usage, and demo subscription changes."""

from fastapi import APIRouter, Header, Request

from app.api.dependencies import AdminUser, ContainerDependency, CurrentUser, DatabaseDependency
from app.api.request_body import read_bounded_body
from app.domain.errors import ConflictError
from app.domain.models import ChangePlanInput, CheckoutLink, PlanOut, SubscriptionOut
from app.services.billing import (
    create_billing_portal,
    handle_billing_webhook,
    list_plans,
    start_plan_change,
    subscription_out,
)

router = APIRouter(prefix="/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/webhooks/stripe", tags=["stripe-webhooks"])


@router.get("/plans", response_model=list[PlanOut])
def plans(_: CurrentUser, db: DatabaseDependency) -> list[PlanOut]:
    return list_plans(db)


@router.get("/subscription", response_model=SubscriptionOut)
def subscription(
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> SubscriptionOut:
    return subscription_out(
        db,
        user.organization_id,
        free_access=container.settings.free_access_mode,
    )


@router.get("/capabilities")
def billing_capabilities(
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> dict[str, object]:
    free_access = container.settings.free_access_mode
    current = subscription_out(
        db,
        user.organization_id,
        free_access=free_access,
    )
    provider = container.billing_provider.name
    checkout_available = not free_access and provider in {"stripe", "demo"}
    return {
        "provider": "internal" if free_access else provider,
        "status": (
            "free_access"
            if free_access
            else "configured"
            if checkout_available
            else "coming_after_core"
        ),
        "free_access": free_access,
        "checkout_available": checkout_available,
        "portal_available": (
            not free_access and provider == "stripe" and current.provider == "stripe"
        ),
    }


@router.post("/subscription", response_model=SubscriptionOut | CheckoutLink)
def update_subscription(
    payload: ChangePlanInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> SubscriptionOut | CheckoutLink:
    if container.settings.free_access_mode:
        raise ConflictError(
            "Free access is active; no subscription checkout session is created",
            details={"free_access": True, "checkout_created": False},
        )
    return start_plan_change(
        db,
        user.organization_id,
        payload.plan_key,
        container.settings.public_base_url,
        container.billing_provider,
    )


@router.post("/portal", response_model=CheckoutLink)
def billing_portal(
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> CheckoutLink:
    if container.settings.free_access_mode:
        raise ConflictError(
            "Free access is active; no billing portal is required",
            details={"free_access": True},
        )
    return create_billing_portal(
        db,
        user.organization_id,
        container.settings.public_base_url,
        container.billing_provider,
    )


@webhook_router.post("/billing")
async def stripe_billing_webhook(
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
) -> dict[str, bool]:
    body = await read_bounded_body(request, max_bytes=1024 * 1024, label="Stripe webhook")
    processed = handle_billing_webhook(
        db,
        container.billing_provider,
        body,
        stripe_signature,
    )
    return {"received": True, "processed": processed}
