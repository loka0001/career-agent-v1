"""Compatibility exports for the split models modules."""

from __future__ import annotations

from app.db.model_groups.automation import (
    AutomationModel,
    AutomationRunModel,
    ContentCampaignModel,
    ContentItemModel,
    ContentVersionModel,
    OpportunityActionModel,
    OpportunityModel,
    StoreBrandModel,
)
from app.db.model_groups.billing import (
    AIUsageRecordModel,
    PaymentTransactionModel,
    PlanModel,
    StripeEventModel,
    SubscriptionModel,
    UsageRecordModel,
)
from app.db.model_groups.catalog import (
    ExternalProductMappingModel,
    InventoryTransactionModel,
    ProductModel,
    ProductVariantModel,
)
from app.db.model_groups.content import (
    MarketingPackModel,
    PolicyModel,
    PublicationModel,
    SalesQueryModel,
)
from app.db.model_groups.customers import (
    ConversationModel,
    CustomerConsentModel,
    CustomerIdentityModel,
    CustomerModel,
    MessageModel,
    ProviderWebhookEventModel,
)
from app.db.model_groups.identity import (
    AuthSessionModel,
    AuthTokenModel,
    MembershipModel,
    OrganizationModel,
    StoreModel,
    StoreSettingsModel,
    UserModel,
)
from app.db.model_groups.integrations import (
    ChannelModel,
    ChannelTemplateModel,
    OAuthTransactionModel,
    ProviderConnectionModel,
)
from app.db.model_groups.orders import (
    ExternalOrderMappingModel,
    OrderItemModel,
    OrderModel,
    OrderTransitionModel,
)
from app.db.model_groups.platform import (
    ApiKeyModel,
    AuditEventModel,
    BackgroundJobModel,
    DataDeletionRequestModel,
    EventModel,
    ExternalOperationModel,
    MediaAssetModel,
    RateLimitBucketModel,
    RetentionPolicyModel,
)
from app.db.model_groups.shared import utc_now

__all__ = [
    "AIUsageRecordModel",
    "ApiKeyModel",
    "AuditEventModel",
    "AuthSessionModel",
    "AuthTokenModel",
    "AutomationModel",
    "AutomationRunModel",
    "BackgroundJobModel",
    "ChannelModel",
    "ChannelTemplateModel",
    "ContentCampaignModel",
    "ContentItemModel",
    "ContentVersionModel",
    "ConversationModel",
    "CustomerConsentModel",
    "CustomerIdentityModel",
    "CustomerModel",
    "DataDeletionRequestModel",
    "EventModel",
    "ExternalOperationModel",
    "ExternalOrderMappingModel",
    "ExternalProductMappingModel",
    "InventoryTransactionModel",
    "MarketingPackModel",
    "MediaAssetModel",
    "MembershipModel",
    "MessageModel",
    "OAuthTransactionModel",
    "OpportunityActionModel",
    "OpportunityModel",
    "OrderItemModel",
    "OrderModel",
    "OrderTransitionModel",
    "OrganizationModel",
    "PaymentTransactionModel",
    "PlanModel",
    "PolicyModel",
    "ProductModel",
    "ProductVariantModel",
    "ProviderConnectionModel",
    "ProviderWebhookEventModel",
    "PublicationModel",
    "RateLimitBucketModel",
    "RetentionPolicyModel",
    "SalesQueryModel",
    "StoreBrandModel",
    "StoreModel",
    "StoreSettingsModel",
    "StripeEventModel",
    "SubscriptionModel",
    "UsageRecordModel",
    "UserModel",
    "utc_now",
]
