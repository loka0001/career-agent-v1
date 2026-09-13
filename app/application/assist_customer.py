"""Grounded sales assistant use case with live DB filters and stable citations."""

from __future__ import annotations

import re

from app.config import Settings
from app.domain.enums import CustomerIntent
from app.domain.models import PolicyExcerpt, SalesAssistantResponse
from app.repositories.policy_repository import PolicyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sales_repository import SalesQueryRepository
from app.services.sales_assistant import SalesAssistantService
from app.services.search_index import SearchIndexService


class AssistCustomerUseCase:
    def __init__(
        self,
        products: ProductRepository,
        policies: PolicyRepository,
        queries: SalesQueryRepository,
        search_index: SearchIndexService,
        sales: SalesAssistantService,
        settings: Settings,
    ):
        self._products = products
        self._policies = policies
        self._queries = queries
        self._search_index = search_index
        self._sales = sales
        self._minimum_score = settings.retrieval_min_score

    def execute(self, store_id: str, message: str) -> SalesAssistantResponse:
        categories = self._products.categories(store_id)
        need = self._sales.extract_need(message, categories)
        active_products = {
            item.product_id: item for item in self._products.list(store_id, active_only=True)
        }

        referenced_ids = {
            token.upper()
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{2,63}\b", message)
            if any(character.isdigit() for character in token)
        }
        has_product_constraints = bool(
            need.categories
            or need.required_features
            or need.use_cases
            or need.max_budget is not None
        )
        if referenced_ids:
            # An explicit catalog identifier is a hard constraint. Unknown or
            # unavailable identifiers must not silently turn into unrelated products.
            candidates = [
                product
                for product_id, product in active_products.items()
                if product_id.upper() in referenced_ids
            ]
        elif has_product_constraints:
            product_hits = self._search_index.search_product_ids(store_id, message, top_k=7)
            candidate_ids = [
                str(hit["product_id"])
                for hit in product_hits
                if float(hit["score"]) >= self._minimum_score
            ]
            candidates = [
                active_products[product_id]
                for product_id in candidate_ids
                if product_id in active_products
            ]
        else:
            candidates = []
        product_intents = {
            CustomerIntent.PRODUCT_SEARCH,
            CustomerIntent.PRODUCT_QUESTION,
            CustomerIntent.PRODUCT_COMPARISON,
        }
        if need.intent not in product_intents:
            candidates = []
        elif not candidates and has_product_constraints and not referenced_ids:
            candidates = list(active_products.values())
        recommendations = self._sales.recommend(candidates, need)

        policy_hits = self._search_index.search_policy_refs(store_id, message, top_k=4)
        policy_rows = {row.source_ref: row for row in self._policies.rows(store_id)}
        policies: list[PolicyExcerpt] = []
        if need.intent == CustomerIntent.POLICY_QUESTION:
            for hit in policy_hits:
                source_ref = str(hit["source_ref"])
                row = policy_rows.get(source_ref)
                if row is not None and float(hit["score"]) >= self._minimum_score:
                    policies.append(
                        PolicyExcerpt(
                            source_ref=row.source_ref,
                            title=row.title,
                            body=row.body,
                            score=float(hit["score"]),
                        )
                    )
        response = self._sales.respond(
            message=message,
            need=need,
            recommendations=recommendations,
            policies=policies,
        )
        self._queries.save(store_id, message, response)
        return response
