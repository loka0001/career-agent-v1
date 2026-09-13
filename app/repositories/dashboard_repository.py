"""Read-only aggregate queries that power the merchant dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    MarketingPackModel,
    ProductModel,
    PublicationModel,
    SalesQueryModel,
)
from app.domain.enums import MarketingStatus, Platform, ProductStatus, PublicationStatus
from app.domain.models import (
    CategoryCount,
    DashboardContentStats,
    DashboardLowStockProduct,
    DashboardProductStats,
    DashboardPublishingStats,
    DashboardRecentPublication,
    DashboardRecentQuery,
    DashboardSalesStats,
    DashboardSnapshot,
)

LOW_STOCK_THRESHOLD = 5
RECENT_LIMIT = 5
SUCCESS_STATUSES = {PublicationStatus.DEMO.value, PublicationStatus.PUBLISHED.value}


class DashboardRepository:
    """Aggregates authoritative store data for the overview screen."""

    def __init__(self, session: Session):
        self._session = session

    def snapshot(self, store_id: str) -> DashboardSnapshot:
        return DashboardSnapshot(
            products=self._product_stats(store_id),
            content=self._content_stats(store_id),
            publishing=self._publishing_stats(store_id),
            sales=self._sales_stats(store_id),
            low_stock_products=self._low_stock_products(store_id),
            recent_publications=self._recent_publications(store_id),
            generated_at=datetime.now(UTC),
        )

    def _product_stats(self, store_id: str) -> DashboardProductStats:
        rows = self._session.execute(
            select(ProductModel.status, ProductModel.stock, ProductModel.price_numeric).where(
                ProductModel.store_id == store_id
            )
        ).all()
        total = len(rows)
        active = sum(1 for status, _, _ in rows if status == ProductStatus.ACTIVE.value)
        in_review = sum(1 for status, _, _ in rows if status != ProductStatus.ACTIVE.value)
        out_of_stock = sum(1 for _, stock, _ in rows if stock == 0)
        low_stock = sum(1 for _, stock, _ in rows if 0 < stock <= LOW_STOCK_THRESHOLD)
        inventory_value = sum(
            (Decimal(price) * stock for _, stock, price in rows), start=Decimal("0")
        )
        category_rows = self._session.execute(
            select(ProductModel.category, func.count())
            .where(ProductModel.store_id == store_id)
            .group_by(ProductModel.category)
            .order_by(func.count().desc(), ProductModel.category)
        ).all()
        return DashboardProductStats(
            total=total,
            active=active,
            in_review=in_review,
            out_of_stock=out_of_stock,
            low_stock=low_stock,
            inventory_value=inventory_value,
            categories=[
                CategoryCount(category=category, count=count) for category, count in category_rows
            ],
        )

    def _content_stats(self, store_id: str) -> DashboardContentStats:
        rows = self._session.execute(
            select(MarketingPackModel.status, func.count())
            .where(MarketingPackModel.store_id == store_id)
            .group_by(MarketingPackModel.status)
        ).all()
        counts = {status: count for status, count in rows}
        published = counts.get(MarketingStatus.PUBLISHED.value, 0) + counts.get(
            MarketingStatus.PARTIAL.value, 0
        )
        return DashboardContentStats(
            total_packs=sum(counts.values()),
            approved=counts.get(MarketingStatus.APPROVED.value, 0),
            published=published,
            drafts=counts.get(MarketingStatus.DRAFT.value, 0),
        )

    def _publishing_stats(self, store_id: str) -> DashboardPublishingStats:
        rows = self._session.execute(
            select(PublicationModel.status, PublicationModel.platform, func.count())
            .join(
                MarketingPackModel,
                PublicationModel.marketing_pack_id == MarketingPackModel.id,
            )
            .where(MarketingPackModel.store_id == store_id)
            .group_by(PublicationModel.status, PublicationModel.platform)
        ).all()
        total = succeeded = failed = facebook = instagram = 0
        for status, platform, count in rows:
            total += count
            if status in SUCCESS_STATUSES:
                succeeded += count
                if platform == Platform.FACEBOOK.value:
                    facebook += count
                elif platform == Platform.INSTAGRAM.value:
                    instagram += count
            elif status == PublicationStatus.FAILED.value:
                failed += count
        return DashboardPublishingStats(
            total=total,
            succeeded=succeeded,
            failed=failed,
            facebook=facebook,
            instagram=instagram,
        )

    def _sales_stats(self, store_id: str) -> DashboardSalesStats:
        total = self._session.scalar(
            select(func.count())
            .select_from(SalesQueryModel)
            .where(SalesQueryModel.store_id == store_id)
        )
        recent_rows = self._session.scalars(
            select(SalesQueryModel)
            .where(SalesQueryModel.store_id == store_id)
            .order_by(SalesQueryModel.created_at.desc(), SalesQueryModel.id.desc())
            .limit(RECENT_LIMIT)
        ).all()
        recommendation_rows = self._session.scalars(
            select(SalesQueryModel.recommended_product_ids_json).where(
                SalesQueryModel.store_id == store_id
            )
        ).all()
        return DashboardSalesStats(
            total_queries=int(total or 0),
            # PostgreSQL's ``json`` type has no equality operator, so comparing
            # this portable SQLAlchemy JSON column with ``[]`` breaks the live
            # dashboard. Count the small per-store result set in Python instead.
            answered_with_recommendations=sum(bool(row) for row in recommendation_rows),
            recent=[
                DashboardRecentQuery(
                    id=row.id,
                    message=row.message,
                    intent=str(row.parsed_need_json.get("intent", "unsupported")),
                    recommendation_count=len(row.recommended_product_ids_json),
                    created_at=row.created_at,
                )
                for row in recent_rows
            ],
        )

    def _low_stock_products(self, store_id: str) -> list[DashboardLowStockProduct]:
        rows = self._session.scalars(
            select(ProductModel)
            .where(
                ProductModel.store_id == store_id,
                ProductModel.stock <= LOW_STOCK_THRESHOLD,
            )
            .order_by(
                ProductModel.stock.asc(),
                ProductModel.updated_at.desc(),
                ProductModel.id.desc(),
            )
            .limit(RECENT_LIMIT)
        ).all()
        return [
            DashboardLowStockProduct(
                product_id=row.product_id,
                name=row.name,
                stock=row.stock,
                price=Decimal(row.price_numeric),
                image_url=row.public_image_url or row.original_image_url,
            )
            for row in rows
        ]

    def _recent_publications(self, store_id: str) -> list[DashboardRecentPublication]:
        rows = self._session.execute(
            select(PublicationModel, ProductModel.name)
            .join(
                MarketingPackModel,
                PublicationModel.marketing_pack_id == MarketingPackModel.id,
            )
            .join(ProductModel, MarketingPackModel.product_pk == ProductModel.id)
            .where(MarketingPackModel.store_id == store_id)
            .order_by(PublicationModel.attempted_at.desc(), PublicationModel.id.desc())
            .limit(RECENT_LIMIT)
        ).all()
        return [
            DashboardRecentPublication(
                publication_id=publication.id,
                product_name=product_name,
                platform=Platform(publication.platform),
                success=publication.status in SUCCESS_STATUSES,
                permalink=publication.permalink,
                attempted_at=publication.attempted_at,
            )
            for publication, product_name in rows
        ]
