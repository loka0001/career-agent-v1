"""Generate separate Facebook and Instagram content from reviewed product facts."""

from app.db.models import ProductModel
from app.domain.enums import ProductStatus
from app.domain.errors import ConflictError
from app.domain.models import MarketingPack
from app.repositories.content_repository import ContentRepository
from app.repositories.product_repository import ProductRepository
from app.services.marketing import MarketingService


class GenerateMarketingPackUseCase:
    def __init__(
        self,
        products: ProductRepository,
        content: ContentRepository,
        marketing: MarketingService,
    ):
        self._products = products
        self._content = content
        self._marketing = marketing

    def execute(self, store_id: str, product_id: str) -> MarketingPack:
        product = self._products.get(store_id, product_id)
        if product.status not in {ProductStatus.REVIEWED, ProductStatus.ACTIVE}:
            raise ConflictError("Product must be reviewed before marketing generation")
        brief, warnings = self._marketing.generate(product)
        row: ProductModel = self._products.get_row(store_id, product_id)
        image_url = product.public_image_url or product.original_image_url
        return self._content.create(
            store_id=store_id,
            product=row,
            facebook_message=brief.facebook_message,
            instagram_caption=brief.instagram_caption,
            hashtags=brief.hashtags,
            image_url=image_url,
            warnings=warnings,
        )
