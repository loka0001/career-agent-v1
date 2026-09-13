"""Deterministic guardrails for files, product facts, marketing, and replies."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.errors import GroundingError, InvalidInputError
from app.domain.models import PolicyExcerpt, ProductRecord, SalesAssistantResponse

IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
PRICE_PATTERN = re.compile(
    r"(?:(?:EGP|جنيه)\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:EGP|جنيه)", re.IGNORECASE
)
DISCOUNT_PATTERN = re.compile(
    r"\b(discount|sale|offer|خصم|تخفيض|عرض خاص|limited stock|كمية محدودة)\b",
    re.IGNORECASE,
)
ABSOLUTE_CLAIM_PATTERN = re.compile(
    r"\b(best|guaranteed|100% guaranteed|الأفضل|مضمون 100%|ضمان كامل)\b",
    re.IGNORECASE,
)
PROMPT_CONTROL_PATTERN = re.compile(
    r"\b(?:ignore (?:all |the )?(?:previous |prior )?instructions|"
    r"system (?:prompt|override)|developer message|jailbreak|override accepted)\b",
    re.IGNORECASE,
)
HIGH_RISK_FACT_PATTERNS: dict[str, re.Pattern[str]] = {
    "bluetooth": re.compile(r"bluetooth|بلوتوث", re.IGNORECASE),
    "wifi": re.compile(r"wi[- ]?fi|واي فاي", re.IGNORECASE),
    "active_noise_cancellation": re.compile(
        r"active noise canc(?:ellation|elling)|إلغاء (?:ال)?ضوضاء", re.IGNORECASE
    ),
    "water_resistance": re.compile(
        r"water(?:proof| resistant)|مقاوم(?:ة)? للماء|IPX\d", re.IGNORECASE
    ),
    "battery": re.compile(r"battery|بطارية", re.IGNORECASE),
    "microphone": re.compile(r"microphone|\bmic\b|ميكروفون", re.IGNORECASE),
    "warranty": re.compile(r"warranty|ضمان", re.IGNORECASE),
}
TECHNICAL_NUMBER_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:W|mAh|hours?|hrs?|ساعة|واط|ml|مل|لتر|GB|TB)\b",
    re.IGNORECASE,
)


def validate_image_file(
    filename: str | None,
    content_type: str | None,
    content: bytes,
    *,
    max_bytes: int,
) -> str:
    if not content:
        raise InvalidInputError("Image file is empty", details={"field": "image"})
    if len(content) > max_bytes:
        raise InvalidInputError(
            "Image is too large", details={"field": "image", "max_bytes": max_bytes}
        )
    if content_type not in IMAGE_SIGNATURES:
        raise InvalidInputError(
            "Unsupported image MIME type",
            details={"allowed": sorted(IMAGE_SIGNATURES)},
        )
    if not any(content.startswith(signature) for signature in IMAGE_SIGNATURES[content_type]):
        raise InvalidInputError("Image signature does not match its MIME type")
    if content_type == "image/webp" and (len(content) < 12 or content[8:12] != b"WEBP"):
        raise InvalidInputError("Invalid WebP signature")
    suffix = Path(filename or "").suffix.casefold()
    expected = {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
    }[content_type]
    if suffix and suffix not in expected:
        raise InvalidInputError("Image extension does not match its MIME type")
    return content_type


def normalize_fact(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def merge_features(raw_features: list[str], visible_features: list[str]) -> list[str]:
    merged: dict[str, str] = {}
    for feature in [*raw_features, *visible_features]:
        cleaned = " ".join(feature.strip().split())
        if cleaned:
            merged.setdefault(normalize_fact(cleaned), cleaned)
    return list(merged.values())


def unsupported_fact_claims(text: str, allowed_facts: str) -> list[str]:
    """Detect common high-risk technical claims absent from the factual allowlist."""

    unsupported = [
        name
        for name, pattern in HIGH_RISK_FACT_PATTERNS.items()
        if pattern.search(text) and not pattern.search(allowed_facts)
    ]
    normalized_allowed = normalize_fact(allowed_facts)
    for match in TECHNICAL_NUMBER_PATTERN.finditer(text):
        claim = normalize_fact(match.group(0))
        if claim not in normalized_allowed:
            unsupported.append(f"technical_spec:{claim}")
    return sorted(set(unsupported))


def validate_marketing_content(
    product: ProductRecord,
    facebook_message: str,
    instagram_caption: str,
) -> list[str]:
    warnings: list[str] = []
    combined = f"{facebook_message}\n{instagram_caption}"
    for match in PRICE_PATTERN.finditer(combined):
        mentioned = Decimal(match.group(1).replace(",", "."))
        if mentioned != product.price:
            warnings.append(
                f"price_mismatch:{format(mentioned, 'f')}!={format(product.price, 'f')}"
            )
    if DISCOUNT_PATTERN.search(combined):
        warnings.append("unsupported_discount_or_scarcity_claim")
    if ABSOLUTE_CLAIM_PATTERN.search(combined):
        warnings.append("unsupported_absolute_claim")
    allowed_facts = "\n".join(
        [
            product.name,
            product.category,
            *product.features,
            *product.customer_benefits,
            product.description,
        ]
    )
    warnings.extend(
        f"unsupported_feature_claim:{claim}"
        for claim in unsupported_fact_claims(combined, allowed_facts)
    )
    return sorted(set(warnings))


def approved_content_hash(
    facebook_message: str,
    instagram_caption: str,
    hashtags: list[str],
    version: int,
) -> str:
    payload = json.dumps(
        {
            "facebook_message": facebook_message,
            "instagram_caption": instagram_caption,
            "hashtags": hashtags,
            "version": version,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approval_snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Return a stable digest for the exact content a merchant approved."""

    payload = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_sales_response(
    response: SalesAssistantResponse,
    products: dict[str, ProductRecord],
    retrieved_citations: set[str],
    policies: list[PolicyExcerpt] | None = None,
) -> None:
    if len(response.recommendations) > 3:
        raise GroundingError("More than three recommendations")
    recommendation_ids = {item.product_id for item in response.recommendations}
    for recommendation in response.recommendations:
        product = products.get(recommendation.product_id)
        if product is None:
            raise GroundingError("Unknown recommended product")
        if product.stock <= 0:
            raise GroundingError("Out-of-stock product recommended")
        if response.need.max_budget is not None and product.price > response.need.max_budget:
            raise GroundingError("Over-budget product recommended")
    for citation in response.citations:
        if citation not in retrieved_citations:
            raise GroundingError("Unknown citation")
    required_product_citations = {f"product:{product_id}" for product_id in recommendation_ids}
    if not required_product_citations.issubset(response.citations):
        raise GroundingError("Recommended product is missing its citation")
    if policies and not any(item.source_ref in response.citations for item in policies):
        raise GroundingError("Policy response is missing a retrieved citation")
    if DISCOUNT_PATTERN.search(response.reply):
        raise GroundingError("Reply contains an unsupported discount or scarcity claim")
    if ABSOLUTE_CLAIM_PATTERN.search(response.reply):
        raise GroundingError("Reply contains an unsupported absolute claim")
    if PROMPT_CONTROL_PATTERN.search(response.reply):
        raise GroundingError("Reply contains prompt-control language")
    for product_id in re.findall(r"\b[A-Z][A-Z0-9_-]{2,}\b", response.reply):
        if product_id.startswith("P") and product_id not in recommendation_ids:
            raise GroundingError("Reply mentions an unrecommended product")
    for match in PRICE_PATTERN.finditer(response.reply):
        mentioned = Decimal(match.group(1).replace(",", "."))
        if not any(product.price == mentioned for product in products.values()):
            raise GroundingError("Reply contains an unsupported price")
    allowed_facts = "\n".join(
        [
            *(
                fact
                for product in products.values()
                for fact in [
                    product.name,
                    product.category,
                    *product.features,
                    *product.customer_benefits,
                    product.description,
                ]
            ),
            *(fact for policy in policies or [] for fact in [policy.title, policy.body]),
        ]
    )
    if unsupported_fact_claims(response.reply, allowed_facts):
        raise GroundingError("Reply contains an unsupported feature claim")
