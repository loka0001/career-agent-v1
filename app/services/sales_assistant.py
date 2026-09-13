"""Deterministic filtering/ranking and grounded response construction."""

from __future__ import annotations

from app.domain.models import (
    CustomerNeed,
    PolicyExcerpt,
    ProductRecord,
    Recommendation,
    SalesAssistantResponse,
)
from app.domain.ranking import apply_business_filters, rank_products
from app.domain.validators import validate_sales_response
from app.integrations.ai_provider import AIProvider, DeterministicAIProvider


class SalesAssistantService:
    def __init__(self, ai_provider: AIProvider):
        self._ai = ai_provider
        self._fallback = DeterministicAIProvider()

    def extract_need(self, message: str, categories: list[str]) -> CustomerNeed:
        return self._ai.extract_customer_need(message, categories)

    def recommend(self, products: list[ProductRecord], need: CustomerNeed) -> list[Recommendation]:
        filtered = apply_business_filters(products, need)
        return [
            Recommendation(
                product_id=product.product_id,
                score=score.total,
                reasons=list(score.reasons),
                product=product,
            )
            for product, score in rank_products(filtered, need)
        ]

    def respond(
        self,
        *,
        message: str,
        need: CustomerNeed,
        recommendations: list[Recommendation],
        policies: list[PolicyExcerpt],
    ) -> SalesAssistantResponse:
        product_map = {item.product_id: item.product for item in recommendations}
        citations = {f"product:{item.product_id}" for item in recommendations}
        citations.update(item.source_ref for item in policies)
        if not recommendations and not policies:
            fallback = self._fallback.generate_grounded_reply(
                message, need, recommendations, policies
            )
            response = SalesAssistantResponse(
                need=need,
                recommendations=[],
                reply=fallback.reply,
                citations=fallback.citations,
                insufficient_context=True,
            )
            validate_sales_response(response, {}, set(), policies)
            return response
        validation_errors: list[str] = []
        for attempt in range(2):
            grounded = self._ai.generate_grounded_reply(
                message,
                need,
                recommendations,
                policies,
                validation_errors=validation_errors or None,
            )
            response = SalesAssistantResponse(
                need=need,
                recommendations=recommendations,
                reply=grounded.reply,
                citations=grounded.citations,
                insufficient_context=not recommendations and not policies,
            )
            try:
                validate_sales_response(response, product_map, citations, policies)
                return response
            except Exception as exc:
                validation_errors = [str(exc)]
                if attempt == 1:
                    break
        fallback = self._fallback.generate_grounded_reply(
            message, need, recommendations, policies, validation_errors=validation_errors
        )
        response = SalesAssistantResponse(
            need=need,
            recommendations=recommendations,
            reply=fallback.reply,
            citations=fallback.citations,
            insufficient_context=not recommendations and not policies,
        )
        validate_sales_response(response, product_map, citations, policies)
        return response
