"""Generated integrations slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.domain.enums import ChannelMode, ChannelType
from app.domain.model_groups.shared import ContractModel


class MetaChannelSettingsInput(ContractModel):
    channel_type: ChannelType
    mode: ChannelMode = ChannelMode.DEMO
    display_name: str = Field(min_length=1, max_length=160)
    account_id: str = Field(default="", max_length=160)
    access_token: str = Field(default="", max_length=4096)
    app_secret: str = Field(default="", max_length=512)
    verify_token: str = Field(default="", max_length=512)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    token_expires_at: datetime | None = None
    is_active: bool = True


class MetaChannelStatus(ContractModel):
    channel_id: int
    channel_type: ChannelType
    mode: ChannelMode
    display_name: str
    configured: bool
    is_active: bool
    masked_account_id: str | None = None
    permissions: list[str] = Field(default_factory=list)
    missing_permissions: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None
    token_expiring: bool = False
    webhook_path: str


class MetaOAuthStart(ContractModel):
    authorization_url: str
    state: str
    demo: bool


class MetaAccountOption(ContractModel):
    page_id: str
    page_name: str
    instagram_account_id: str | None = None
    instagram_username: str | None = None


class MetaOAuthExchangeInput(ContractModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=20, max_length=8192)


class MetaOAuthExchangeResult(ContractModel):
    transaction_id: str
    accounts: list[MetaAccountOption]


class MetaOAuthConnectInput(ContractModel):
    transaction_id: str = Field(min_length=20, max_length=64)
    page_id: str = Field(min_length=1, max_length=160)
    instagram_account_id: str | None = Field(default=None, max_length=160)


class ProviderConnectionOut(ContractModel):
    id: str
    provider: str
    connection_type: str
    mode: str
    display_name: str
    external_account_id: str | None = None
    external_business_id: str | None = None
    external_resource_id: str
    scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    status: str
    token_expires_at: datetime | None = None
    token_expiring: bool = False
    last_health_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    last_error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class CommerceConnectionInput(ContractModel):
    provider: Literal["shopify", "woocommerce", "generic_website"]
    display_name: str = Field(min_length=1, max_length=160)
    store_url: str = Field(min_length=8, max_length=500)
    access_token: str = Field(default="", max_length=4096)
    consumer_key: str = Field(default="", max_length=512)
    consumer_secret: str = Field(default="", max_length=4096)
    webhook_secret: str = Field(default="", max_length=4096)
    install_webhooks: bool = True


class ShopifyOAuthStartInput(ContractModel):
    display_name: str = Field(min_length=1, max_length=160)
    shop: str = Field(min_length=4, max_length=255)
    install_webhooks: bool = True


class ShopifyOAuthStart(ContractModel):
    authorization_url: str
    state: str
    shop: str


class ShopifyOAuthExchangeInput(ContractModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=20, max_length=8192)
    shop: str = Field(min_length=4, max_length=255)
    hmac: str = Field(min_length=32, max_length=256)
    timestamp: str = Field(min_length=1, max_length=64)
    host: str | None = Field(default=None, max_length=512)


class CommerceSyncResult(ContractModel):
    connection_id: str
    products_created: int
    products_updated: int
    orders_created: int
    orders_updated: int
    synced_at: datetime
