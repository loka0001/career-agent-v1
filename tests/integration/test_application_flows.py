from __future__ import annotations

import uuid

from sqlalchemy import select

from app.application.approve_and_publish import MarketingLifecycleUseCase, PublisherSet
from app.application.assist_customer import AssistCustomerUseCase
from app.application.generate_marketing_pack import GenerateMarketingPackUseCase
from app.db.models import SalesQueryModel
from app.domain.enums import CustomerIntent, Platform
from app.domain.errors import ExternalProviderError
from app.domain.models import PublishResult
from app.integrations.facebook import FakeFacebookPublisher
from app.repositories.audit_repository import AuditRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.policy_repository import PolicyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publication_repository import PublicationRepository
from app.repositories.sales_repository import SalesQueryRepository
from app.services.marketing import MarketingService
from app.services.sales_assistant import SalesAssistantService
from app.services.search_index import SearchIndexService
from tests.conftest import TestContext


class FailingInstagramPublisher:
    def publish(self, image_url: str, caption: str) -> PublishResult:
        del image_url, caption
        raise ExternalProviderError("temporary provider failure")

    def check_connection(self) -> bool:
        return False


def test_sales_assistant_uses_seeded_db_and_respects_budget(context: TestContext) -> None:
    with context.session_factory.begin() as session:
        use_case = AssistCustomerUseCase(
            ProductRepository(session),
            PolicyRepository(session),
            SalesQueryRepository(session),
            SearchIndexService(context.container.vector_store),
            SalesAssistantService(context.container.ai_provider),
            context.container.settings,
        )
        response = use_case.execute(
            "demo-store",
            "عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه",
        )
        stored_query = session.scalar(
            select(SalesQueryModel).order_by(SalesQueryModel.id.desc()).limit(1)
        )
        assert stored_query is not None
        assert stored_query.message.startswith("sha256:")
        assert stored_query.response_text.startswith("sha256:")
    assert response.need.intent == CustomerIntent.PRODUCT_SEARCH
    assert 1 <= len(response.recommendations) <= 3
    assert all(item.product.stock > 0 for item in response.recommendations)
    assert all(item.product.price <= 1500 for item in response.recommendations)
    assert set(response.citations) == {
        f"product:{item.product_id}" for item in response.recommendations
    }


def test_policy_question_returns_stable_policy_citation(context: TestContext) -> None:
    with context.session_factory.begin() as session:
        use_case = AssistCustomerUseCase(
            ProductRepository(session),
            PolicyRepository(session),
            SalesQueryRepository(session),
            SearchIndexService(context.container.vector_store),
            SalesAssistantService(context.container.ai_provider),
            context.container.settings,
        )
        response = use_case.execute("demo-store", "ما هي سياسة الاسترجاع؟")
    assert response.need.intent == CustomerIntent.POLICY_QUESTION
    assert "policy:returns-ar-v1" in response.citations
    assert not response.recommendations


def test_publish_saves_partial_success_instead_of_hiding_failure(
    context: TestContext,
) -> None:
    with context.session_factory.begin() as session:
        content = ContentRepository(session)
        marketing = MarketingService(context.container.ai_provider)
        pack = GenerateMarketingPackUseCase(ProductRepository(session), content, marketing).execute(
            "demo-store", "A101"
        )
        lifecycle = MarketingLifecycleUseCase(
            content,
            PublicationRepository(session),
            AuditRepository(session),
            marketing,
            PublisherSet(FakeFacebookPublisher(), FailingInstagramPublisher()),
        )
        lifecycle.approve("demo-store", pack.id, "merchant@example.com")
        results = lifecycle.publish(
            "demo-store",
            pack.id,
            [Platform.FACEBOOK, Platform.INSTAGRAM],
            f"partial-{uuid.uuid4().hex}",
            "merchant@example.com",
        )
        saved_pack = content.get(pack.id, "demo-store")
    assert [item.success for item in results] == [True, False]
    assert results[1].error_code == "external_provider_error"
    assert saved_pack.status == "partial"
