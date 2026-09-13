"""Public, grounded sales-assistant endpoint."""

from decimal import Decimal

from fastapi import APIRouter

from app.api.dependencies import ContainerDependency, CurrentUser, DatabaseDependency
from app.application.assist_customer import AssistCustomerUseCase
from app.domain.errors import InvalidInputError
from app.domain.models import SalesAssistantResponse, SalesAssistInput
from app.repositories.policy_repository import PolicyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sales_repository import SalesQueryRepository
from app.services.ai_usage import record_ai_operation
from app.services.billing import check_and_increment, require_feature
from app.services.sales_assistant import SalesAssistantService
from app.services.search_index import SearchIndexService

router = APIRouter(prefix="/sales", tags=["sales"])


def build_assist_use_case(container: ContainerDependency, db: DatabaseDependency) -> AssistCustomerUseCase:
    return AssistCustomerUseCase(
        ProductRepository(db),
        PolicyRepository(db),
        SalesQueryRepository(db),
        SearchIndexService(container.vector_store),
        SalesAssistantService(container.ai_provider),
        container.settings,
    )


@router.post(
    "/assist",
    response_model=SalesAssistantResponse,
    summary="Recommend up to three products using the authenticated store's facts",
)
def assist_customer(
    payload: SalesAssistInput,
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> SalesAssistantResponse:
    require_feature(db, user.store_id, "inbox")
    if len(payload.message) > container.settings.max_customer_message_length:
        raise InvalidInputError(
            "Customer message is too long",
            details={"max_length": container.settings.max_customer_message_length},
        )
    check_and_increment(db, user.store_id, "ai_operations")
    result = build_assist_use_case(container, db).execute(
        user.store_id, payload.message
    )
    record_ai_operation(
        db,
        user.store_id,
        "sales_assist",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
        cost=(
            Decimal("0")
            if container.settings.ai_provider == "deterministic"
            else None
        ),
    )
    return result
