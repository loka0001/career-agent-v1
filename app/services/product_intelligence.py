"""Product image analysis, fact merge, and informational copy generation."""

from app.domain.models import ImageAnalysis, ProductCopy, ProductCreateInput
from app.domain.validators import merge_features
from app.integrations.ai_provider import AIProvider


class ProductIntelligenceService:
    def __init__(self, ai_provider: AIProvider):
        self._ai = ai_provider

    def analyze(
        self,
        product: ProductCreateInput,
        image: bytes,
        mime_type: str,
    ) -> tuple[ImageAnalysis, list[str], ProductCopy]:
        analysis = self._ai.analyze_product_image(product, image, mime_type)
        features = merge_features(product.raw_features, analysis.visible_features)
        copy = self._ai.generate_product_copy(product, analysis, features)
        return analysis, features, copy
