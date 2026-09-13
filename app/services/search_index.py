"""Search index boundary shared by local Chroma and production SQL search."""

from typing import Any, Protocol

from app.domain.models import PolicyExcerpt, ProductRecord


class SearchStore(Protocol):
    def upsert_product(self, product: ProductRecord) -> None: ...

    def upsert_policy(self, store_id: str, policy: PolicyExcerpt) -> None: ...

    def search_products(
        self, store_id: str, query: str, top_k: int = 7
    ) -> list[dict[str, Any]]: ...

    def search_policies(
        self, store_id: str, query: str, top_k: int = 4
    ) -> list[dict[str, Any]]: ...

    def ready(self) -> bool: ...


class SearchIndexService:
    def __init__(self, store: SearchStore):
        self._store = store

    def index_product(self, product: ProductRecord) -> None:
        self._store.upsert_product(product)

    def index_policy(self, store_id: str, policy: PolicyExcerpt) -> None:
        self._store.upsert_policy(store_id, policy)

    def search_product_ids(self, store_id: str, query: str, top_k: int = 7) -> list[dict[str, Any]]:
        return self._store.search_products(store_id, query, top_k)

    def search_policy_refs(self, store_id: str, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        return self._store.search_policies(store_id, query, top_k)

    def ready(self) -> bool:
        return self._store.ready()
