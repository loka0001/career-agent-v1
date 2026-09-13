"""Merchant review and activation of product facts."""

from app.domain.models import ProductRecord, ProductUpdateInput
from app.repositories.product_repository import ProductRepository
from app.services.search_index import SearchIndexService


class ProductManagementUseCase:
    def __init__(self, products: ProductRepository, search_index: SearchIndexService):
        self._products = products
        self._search_index = search_index

    def review(self, store_id: str, product_id: str, changes: ProductUpdateInput) -> ProductRecord:
        product = self._products.update(store_id, product_id, changes, mark_reviewed=True)
        self._search_index.index_product(product)
        return product

    def activate(self, store_id: str, product_id: str) -> ProductRecord:
        product = self._products.activate(store_id, product_id)
        self._search_index.index_product(product)
        return product
