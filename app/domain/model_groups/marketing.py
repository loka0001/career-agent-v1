"""Generated marketing slice of models.py."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.enums import MarketingStatus, Platform
from app.domain.model_groups.shared import ContractModel, MoneyModel


class MarketingBrief(ContractModel):
    hook: str = Field(min_length=1, max_length=300)
    benefits: list[str] = Field(default_factory=list, max_length=6)
    call_to_action: str = Field(min_length=1, max_length=200)
    hashtags: list[str] = Field(default_factory=list, max_length=15)
    facebook_message: str = Field(min_length=1, max_length=4000)
    instagram_caption: str = Field(min_length=1, max_length=2200)


class MarketingPack(MoneyModel):
    id: int
    product_id: str
    facebook_message: str
    instagram_caption: str
    hashtags: list[str]
    image_url: str
    validation_warnings: list[str]
    version: int
    status: MarketingStatus
    approved_at: datetime | None = None
    approved_by: str | None = None
    created_at: datetime
    updated_at: datetime


class MarketingPackUpdateInput(ContractModel):
    facebook_message: str | None = Field(default=None, min_length=1, max_length=4000)
    instagram_caption: str | None = Field(default=None, min_length=1, max_length=2200)
    hashtags: list[str] | None = Field(default=None, max_length=15)


class PublishResult(ContractModel):
    publication_id: int | None = None
    platform: Platform
    success: bool
    external_id: str | None = None
    permalink: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_status: str | None = None
