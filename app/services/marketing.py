"""Marketing generation plus deterministic factual checks."""

from app.domain.models import MarketingBrief, ProductRecord
from app.domain.validators import validate_marketing_content
from app.integrations.ai_provider import AIProvider


class MarketingService:
    def __init__(self, ai_provider: AIProvider):
        self._ai = ai_provider

    def generate(self, product: ProductRecord) -> tuple[MarketingBrief, list[str]]:
        brief = self._ai.generate_marketing_brief(product)
        warnings = validate_marketing_content(
            product,
            brief.facebook_message,
            brief.instagram_caption,
        )
        return brief, warnings

    @staticmethod
    def validate(product: ProductRecord, facebook: str, instagram: str) -> list[str]:
        return validate_marketing_content(product, facebook, instagram)
