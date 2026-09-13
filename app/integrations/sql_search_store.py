"""Portable SQL-backed retrieval for stateless and horizontally scaled runtimes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import PolicyModel, ProductModel
from app.domain.enums import ProductStatus
from app.domain.models import PolicyExcerpt, ProductRecord
from app.repositories.product_repository import to_product_record
from app.services.retrieval import hash_embedding, lexical_score


def _cosine(left: list[float], right: list[float]) -> float:
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True))))


class SQLSearchStore:
    """Retrieve from authoritative SQL without relying on local vector files."""

    def __init__(self, session_factory: sessionmaker[Session], *, scan_limit: int = 2000):
        self._session_factory = session_factory
        self._scan_limit = scan_limit

    @staticmethod
    def _product_document(product: ProductRecord) -> str:
        return "\n".join(
            [
                product.name,
                product.category,
                *product.features,
                *product.customer_benefits,
                product.description,
            ]
        )

    def upsert_product(self, product: ProductRecord) -> None:
        del product

    def upsert_policy(self, store_id: str, policy: PolicyExcerpt) -> None:
        del store_id, policy

    @staticmethod
    def _rank(
        query: str,
        rows: list[dict[str, Any]],
        *,
        top_k: int,
    ) -> list[dict[str, Any]]:
        query_vector = hash_embedding(query)
        for row in rows:
            document = str(row["document"])
            lexical = lexical_score(query, document)
            semantic = _cosine(query_vector, hash_embedding(document))
            row["lexical_score"] = round(lexical, 4)
            row["score"] = round(max(lexical, semantic), 4)
        rows.sort(
            key=lambda item: (
                -float(item["lexical_score"]),
                -float(item["score"]),
                str(item.get("product_id") or item.get("source_ref")),
            )
        )
        return rows[:top_k]

    def search_products(self, store_id: str, query: str, top_k: int = 7) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            products = session.scalars(
                select(ProductModel)
                .where(
                    ProductModel.store_id == store_id,
                    ProductModel.status == ProductStatus.ACTIVE.value,
                )
                .order_by(ProductModel.id)
                .limit(self._scan_limit)
            ).all()
        rows = []
        for product_row in products:
            product = to_product_record(product_row)
            rows.append(
                {
                    "product_id": product.product_id,
                    "document": self._product_document(product),
                }
            )
        return self._rank(query, rows, top_k=top_k)

    def search_policies(self, store_id: str, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            policies = session.scalars(
                select(PolicyModel)
                .where(PolicyModel.store_id == store_id)
                .order_by(PolicyModel.id)
                .limit(self._scan_limit)
            ).all()
        rows = [
            {
                "source_ref": row.source_ref,
                "document": f"{row.title}\n{row.body}",
            }
            for row in policies
        ]
        return self._rank(query, rows, top_k=top_k)

    def ready(self) -> bool:
        with self._session_factory() as session:
            session.execute(text("SELECT 1"))
        return True
