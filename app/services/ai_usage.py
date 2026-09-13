"""Persist provider usage and enforce per-store monthly AI spend budgets."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AIUsageRecordModel, StoreSettingsModel
from app.domain.errors import QuotaExceededError
from app.integrations.ai_provider import AIProvider, consume_ai_metrics


def check_ai_budget(session: Session, store_id: str) -> None:
    now = datetime.now(UTC)
    period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    settings = session.get(StoreSettingsModel, store_id)
    budget = (
        Decimal(settings.ai_monthly_budget_numeric) if settings is not None else Decimal("25.00")
    )
    spent = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(AIUsageRecordModel.cost_numeric), 0)).where(
                AIUsageRecordModel.store_id == store_id,
                AIUsageRecordModel.created_at >= period_start,
            )
        )
        or 0
    )
    if spent >= budget:
        raise QuotaExceededError(
            "Monthly AI budget has been reached",
            details={
                "metric": "ai_cost",
                "limit": str(budget),
                "used": str(spent),
                "budget_action_required": True,
            },
        )


def record_ai_operation(
    session: Session,
    store_id: str,
    operation: str,
    provider: str,
    model: str,
    *,
    ai_provider: AIProvider | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost: Decimal | None = None,
    latency_ms: int | None = None,
) -> None:
    metrics = consume_ai_metrics(ai_provider) if ai_provider is not None else None
    if metrics is not None:
        provider = metrics.provider
        model = metrics.model
        input_tokens = metrics.input_tokens
        output_tokens = metrics.output_tokens
        latency_ms = metrics.latency_ms
        cost = metrics.estimated_cost
    session.add(
        AIUsageRecordModel(
            store_id=store_id,
            operation=operation,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_numeric=cost,
            latency_ms=latency_ms,
            cost_source="estimated" if cost is not None else "unknown",
        )
    )
