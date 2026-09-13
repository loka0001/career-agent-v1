"""Persistent Chroma index with deterministic local hash embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api.types import Embeddings, QueryResult

from app.domain.models import PolicyExcerpt, ProductRecord
from app.services.retrieval import hash_embedding, lexical_score


class ChromaStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(directory))
        self._products = self._client.get_or_create_collection(
            "commerce_products", metadata={"hnsw:space": "cosine"}
        )
        self._policies = self._client.get_or_create_collection(
            "commerce_policies", metadata={"hnsw:space": "cosine"}
        )

    @staticmethod
    def product_document(product: ProductRecord) -> str:
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
        document = self.product_document(product)
        self._products.upsert(
            ids=[f"product:{product.store_id}:{product.product_id}"],
            documents=[document],
            embeddings=cast(Embeddings, [hash_embedding(document)]),
            metadatas=[
                {
                    "store_id": product.store_id,
                    "product_id": product.product_id,
                    "status": product.status.value,
                }
            ],
        )

    def upsert_policy(self, store_id: str, policy: PolicyExcerpt) -> None:
        document = f"{policy.title}\n{policy.body}"
        self._policies.upsert(
            ids=[f"policy:{store_id}:{policy.source_ref}"],
            documents=[document],
            embeddings=cast(Embeddings, [hash_embedding(document)]),
            metadatas=[{"store_id": store_id, "source_ref": policy.source_ref}],
        )

    def search_products(self, store_id: str, query: str, top_k: int = 7) -> list[dict[str, Any]]:
        if self._products.count() == 0:
            return []
        result = self._products.query(
            query_embeddings=cast(Embeddings, [hash_embedding(query)]),
            n_results=self._products.count(),
            where={"$and": [{"store_id": store_id}, {"status": "active"}]},
        )
        return self._rerank(self._normalize_results(result, "product_id"), query, top_k)

    def search_policies(self, store_id: str, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if self._policies.count() == 0:
            return []
        result = self._policies.query(
            query_embeddings=cast(Embeddings, [hash_embedding(query)]),
            n_results=self._policies.count(),
            where={"store_id": store_id},
        )
        return self._rerank(self._normalize_results(result, "source_ref"), query, top_k)

    @staticmethod
    def _rerank(results: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
        for result in results:
            semantic = float(result["score"])
            lexical = lexical_score(query, str(result["document"]))
            result["score"] = round(max(semantic, lexical), 4)
            result["lexical_score"] = round(lexical, 4)
        results.sort(
            key=lambda item: (
                -float(item["lexical_score"]),
                -float(item["score"]),
                str(item.get("product_id") or item.get("source_ref")),
            )
        )
        return results[:top_k]

    @staticmethod
    def _normalize_results(result: QueryResult, identity_key: str) -> list[dict[str, Any]]:
        metadatas = (result.get("metadatas") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        normalized: list[dict[str, Any]] = []
        for metadata, document, distance in zip(metadatas, documents, distances, strict=True):
            normalized.append(
                {
                    identity_key: metadata[identity_key],
                    "document": document,
                    "score": round(max(0.0, min(1.0, 1.0 - float(distance))), 4),
                }
            )
        return normalized

    def ready(self) -> bool:
        self._client.heartbeat()
        return True
