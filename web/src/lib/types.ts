export type ProductStatus = "draft" | "reviewed" | "active";
export interface ProductVariantInput {
  variant_id: string;
  title: string;
  sku: string;
  options: Record<string, string>;
  price: string;
  compare_at_price?: string | null;
  stock: number;
  stock_policy: "deny" | "continue";
}
export interface ProductVariant extends ProductVariantInput {
  id: number;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface InventoryAdjustmentInput {
  variant_id?: string | null;
  delta: number;
  reason: string;
  idempotency_key: string;
  allow_negative?: boolean;
  reference_type?: string;
  reference_id?: string;
}
export interface InventoryTransaction {
  id: number;
  product_id: string;
  variant_id: string | null;
  delta: number;
  quantity_before: number;
  quantity_after: number;
  reason: string;
  reference_type: string;
  reference_id: string;
  idempotency_key: string;
  actor_user_id: string | null;
  created_at: string;
}
export type MarketingStatus =
  "draft" | "approved" | "published" | "partial" | "failed";
export type Platform = "facebook" | "instagram";

export interface ProductRecord {
  product_id: string;
  store_id: string;
  name: string;
  category: string;
  price: string;
  stock: number;
  features: string[];
  customer_benefits: string[];
  description: string;
  image_summary: string;
  original_image_url: string;
  public_image_url: string | null;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
  sku?: string;
  currency?: string;
  compare_at_price?: string | null;
  stock_policy?: "deny" | "continue";
  source_of_truth?: "local" | "external";
  source_provider?: string | null;
}

export type ProductUpdateInput = Partial<
  Pick<
    ProductRecord,
    | "name"
    | "category"
    | "price"
    | "stock"
    | "features"
    | "customer_benefits"
    | "description"
    | "sku"
    | "currency"
    | "compare_at_price"
    | "stock_policy"
  >
> & {
  tax?: Record<string, unknown>;
  shipping_metadata?: Record<string, unknown>;
};

export interface MarketingPack {
  id: number;
  product_id: string;
  facebook_message: string;
  instagram_caption: string;
  hashtags: string[];
  image_url: string;
  validation_warnings: string[];
  version: number;
  status: MarketingStatus;
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublishResult {
  publication_id: number | null;
  platform: Platform;
  success: boolean;
  external_id: string | null;
  permalink: string | null;
  error_code: string | null;
  error_message: string | null;
  raw_status: string | null;
}

export interface Recommendation {
  product_id: string;
  score: number;
  reasons: string[];
  product: ProductRecord;
}

export interface SalesResponse {
  need: {
    intent: string;
    categories: string[];
    max_budget: string | null;
    required_features: string[];
    use_cases: string[];
    excluded_features: string[];
    language: string;
  };
  recommendations: Recommendation[];
  reply: string;
  citations: string[];
  insufficient_context: boolean;
}

export interface IntegrationStatus {
  name: string;
  configured: boolean;
  mode: string;
  masked_identifier: string | null;
  last_check: string | null;
}

export interface ProviderConnection {
  id: string;
  provider: string;
  connection_type: string;
  mode: string;
  display_name: string;
  external_account_id: string | null;
  external_business_id: string | null;
  external_resource_id: string;
  scopes: string[];
  capabilities: string[];
  status:
    | "pending"
    | "connected"
    | "degraded"
    | "expired"
    | "action_required"
    | "disconnected";
  token_expires_at: string | null;
  token_expiring: boolean;
  last_health_at: string | null;
  last_successful_sync_at: string | null;
  last_error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommerceSyncResult {
  connection_id: string;
  products_created: number;
  products_updated: number;
  orders_created: number;
  orders_updated: number;
  synced_at: string;
}

export interface WhatsAppSettings {
  channel_id: number | null;
  mode: "demo" | "live";
  demo_available: boolean;
  display_name: string;
  configured: boolean;
  is_active: boolean;
  masked_phone_number_id: string | null;
  masked_waba_id: string | null;
  webhook_path: string;
  embedded_signup_available: boolean;
  connection_status: string;
}

export interface WhatsAppTemplate {
  id: number;
  name: string;
  language: string;
  body: string;
  variables: string[];
  external_id: string | null;
  category: "UTILITY" | "MARKETING" | "AUTHENTICATION";
  status: string;
  rejection_reason: string | null;
  quality_score: string | null;
  last_synced_at: string | null;
  created_at: string;
}

export interface WhatsAppPhoneOption {
  phone_number_id: string;
  waba_id: string;
  display_phone_number: string;
  verified_name: string;
  quality_rating: string;
  verification_status: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export type ChannelType =
  | "webchat"
  | "whatsapp"
  | "instagram_dm"
  | "messenger"
  | "facebook_comments"
  | "instagram_comments";
export type ConversationStatus = "open" | "pending" | "resolved" | "snoozed";
export type ConversationPriority = "low" | "normal" | "high";
export type MessageDirection = "inbound" | "outbound";
export type MessageSenderType =
  "customer" | "agent" | "assistant" | "system" | "note";
export type MessageStatus =
  | "received"
  | "queued"
  | "sending"
  | "sent"
  | "delivered"
  | "read"
  | "failed"
  | "delivery_unknown";

export interface CustomerSummary {
  id: number;
  display_name: string;
  phone: string | null;
  email: string | null;
  tags: string[];
  lead_score: number;
  consent: Record<string, boolean>;
  first_seen_at: string;
  last_seen_at: string;
}

export interface MessageOut {
  id: number;
  direction: MessageDirection;
  sender_type: MessageSenderType;
  body: string;
  attachments: {
    type: string;
    url?: string;
    mime_type?: string;
    filename?: string;
  }[];
  status: MessageStatus;
  external_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  channel_type: ChannelType;
  status: ConversationStatus;
  priority: ConversationPriority;
  customer: CustomerSummary;
  assignee_user_id: string | null;
  last_message_preview: string;
  unread_count: number;
  tags: string[];
  sla_overdue: boolean;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageOut[];
}

export interface DashboardSnapshot {
  products: {
    total: number;
    active: number;
    in_review: number;
    out_of_stock: number;
    low_stock: number;
    inventory_value: string;
    categories: { category: string; count: number }[];
  };
  content: {
    total_packs: number;
    approved: number;
    published: number;
    drafts: number;
  };
  publishing: {
    total: number;
    succeeded: number;
    failed: number;
    facebook: number;
    instagram: number;
  };
  sales: {
    total_queries: number;
    answered_with_recommendations: number;
    recent: {
      id: number;
      message: string;
      intent: string;
      recommendation_count: number;
      created_at: string;
    }[];
  };
  low_stock_products: {
    product_id: string;
    name: string;
    stock: number;
    price: string;
    image_url: string;
  }[];
  recent_publications: {
    publication_id: number;
    product_name: string;
    platform: Platform;
    success: boolean;
    permalink: string | null;
    attempted_at: string;
  }[];
  generated_at: string;
}

export interface Opportunity {
  id: number;
  opportunity_type: string;
  customer_id: number | null;
  related_product_ids: string[];
  reason: string;
  expected_revenue: string;
  realized_revenue: string;
  confidence: number;
  suggested_action: string;
  channel: string | null;
  message: string;
  status: "new" | "awaiting_approval" | "executed" | "won" | "rejected";
  detected_at: string;
}

export interface OpportunityDashboard {
  potential_revenue: string;
  recovered_revenue: string;
  new_count: number;
  awaiting_approval_count: number;
  executed_count: number;
  won_count: number;
  funnel: Record<string, number>;
  top_opportunities: Opportunity[];
}

export interface ScoreSignal {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  explanation: string;
}

export interface CustomerIntelligence {
  customer: CustomerSummary;
  lead_score: number;
  score_signals: ScoreSignal[];
  segments: string[];
  completed_orders: number;
  total_revenue: string;
  average_order_value: string;
  days_since_last_activity: number;
  preferred_product_ids: string[];
  rfm: {
    recency_days: number;
    frequency: number;
    monetary: string;
    recency_score: number;
    frequency_score: number;
    monetary_score: number;
  };
  purchase_probability: number;
  churn_risk: string;
  timeline: {
    event_type: string;
    title: string;
    detail: string;
    occurred_at: string;
  }[];
}

export type OrderStatus =
  | "draft"
  | "pending"
  | "confirmed"
  | "paid"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "refunded";

export interface OrderRecord {
  id: number;
  customer_id: number;
  conversation_id: number | null;
  status: OrderStatus;
  currency: string;
  subtotal: string;
  discount: string;
  shipping_total: string;
  tax_total: string;
  total: string;
  shipping: Record<string, string>;
  notes: string;
  payment_provider: string | null;
  payment_status: string | null;
  fulfillment_status: string;
  provider_references: Record<string, string>;
  refunded_amount: string;
  items: {
    product_id: string;
    variant_id: string | null;
    sku: string;
    options: Record<string, string>;
    product_name: string;
    unit_price: string;
    quantity: number;
    line_total: string;
  }[];
  timeline: {
    from_status: OrderStatus | null;
    to_status: OrderStatus;
    actor_user_id: string | null;
    reason: string;
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
}

export interface DraftOrderInput {
  conversation_id: number;
  items: {
    product_id: string;
    variant_id?: string | null;
    quantity: number;
  }[];
  discount: string;
  shipping_total: string;
  tax_total: string;
  currency: string;
  idempotency_key: string;
  shipping: Record<string, string>;
  notes: string;
}

export interface BrandProfile {
  tone: string;
  audience: string;
  guidelines: string;
  primary_color: string;
  updated_at: string;
}

export interface ContentItem {
  id: number;
  campaign_id: number | null;
  product_id: string;
  content_format: string;
  platform: Platform;
  tone: string;
  title: string;
  body: string;
  caption: string;
  hashtags: string[];
  cta: string;
  validation_warnings: string[];
  status: string;
  current_version: number;
  scheduled_for: string | null;
  published_at: string | null;
  external_id: string | null;
  approved_at: string | null;
  approved_by: string | null;
  approved_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: number;
  name: string;
  goal: string;
  budget: string;
  product_ids: string[];
  concept: string;
  audience: string;
  offer: string;
  landing_copy: string;
  whatsapp_template: string;
  kpis: string[];
  status: string;
  created_at: string;
}

export interface AnalyticsSnapshot {
  period_start: string;
  period_end: string;
  channel: string | null;
  conversation_volume: number;
  first_response_minutes: string | null;
  resolution_minutes: string | null;
  leads: number;
  conversion_rate: string;
  attributed_revenue: string;
  recovered_revenue: string;
  orders_by_channel: Record<string, number>;
  top_products: {
    product_id: string;
    name: string;
    quantity: number;
    revenue: string;
  }[];
  content_published: number;
  content_engagements: number;
  automation_runs: number;
  automation_success_rate: string;
  ai_operations: number;
  ai_cost: string | null;
  agent_performance: { user_id: string; messages_sent: number }[];
  funnel: Record<string, number>;
}

export interface Automation {
  id: number;
  name: string;
  trigger_type: string;
  conditions: { field: string; operator: string; value: unknown }[];
  actions: { action_type: string; config: Record<string, unknown> }[];
  delay_seconds: number;
  approval_required: boolean;
  is_enabled: boolean;
  template_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRun {
  id: number;
  automation_id: number;
  event_key: string;
  event: Record<string, unknown>;
  status: string;
  last_error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface Plan {
  key: "starter" | "growth" | "pro";
  name: string;
  price: string;
  quotas: Record<string, number>;
  features: string[];
}

export interface Subscription {
  plan: Plan;
  status: string;
  provider: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_end: string | null;
  usage: Record<string, number>;
}

export interface BillingCapabilities {
  provider: string;
  status: "configured" | "coming_after_core" | "free_access";
  free_access: boolean;
  checkout_available: boolean;
  portal_available: boolean;
}

export interface CheckoutLink {
  provider: string;
  url: string;
  expires_at: string;
}

export type MemberRole = "analyst" | "agent" | "marketer" | "admin" | "owner";

export interface AuthUser {
  user_id: string;
  email: string;
  full_name: string;
  store_id: string;
  organization_id: string;
  role: MemberRole;
  email_verified: boolean;
  mfa_enabled: boolean;
}

export interface AuthSession {
  session_id: string;
  current: boolean;
  user_agent: string;
  ip_address: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
}

export interface TeamMember {
  membership_id: number;
  user_id: string;
  email: string;
  full_name: string;
  role: MemberRole;
  created_at: string;
}

export interface StoreSettings {
  store_id: string;
  slug: string;
  store_name: string;
  default_language: "ar" | "en";
  business_type: string;
  logo_url: string | null;
  brand_colors: Record<string, string>;
  tone: string;
  assistant_name: string;
  assistant_instructions: string;
  shipping_policy: string;
  return_policy: string;
  ai_monthly_budget: string;
  onboarding_steps: Record<string, boolean>;
  onboarding_completed: boolean;
  updated_at: string;
}

export type StoreSettingsInput = Omit<
  StoreSettings,
  | "store_id"
  | "slug"
  | "updated_at"
  | "onboarding_steps"
  | "onboarding_completed"
>;

export interface RetentionPolicy {
  store_id: string;
  message_days: number;
  media_days: number;
  event_days: number;
  updated_at: string;
}

export interface DeletionRequest {
  request_id: string;
  scope: string;
  status: string;
  execute_after: string;
  requested_at: string;
  completed_at: string | null;
}

export interface OperatorOverview {
  generated_at: string;
  stores: number;
  provider_health: Record<string, number>;
  subscriptions: Record<string, number>;
  ai_cost: string;
  queue: {
    queued: number;
    running: number;
    succeeded: number;
    failed: number;
    oldest_job_age_seconds: number | null;
  };
}

export interface OperatorAlert {
  code: string;
  severity: "warning" | "critical";
  status: "ok" | "firing";
  message: string;
  details: Record<string, string | number | null | Record<string, number>>;
}

export interface OperatorStore {
  id: string;
  name: string;
  slug: string;
  organization_id: string | null;
  status: "active" | "suspended";
  subscription: { plan: string; status: string; provider: string } | null;
  providers: { provider: string; status: string }[];
  quotas: Record<string, number>;
  ai_cost: string;
  created_at: string;
}

export interface OperatorJob {
  id: number;
  store_id: string | null;
  job_type: string;
  status: string;
  attempts: number;
  max_attempts: number;
  run_at: string;
  last_error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface OnboardingStep {
  key: string;
  title: string;
  complete: boolean;
  required: boolean;
  href: string;
  evidence: string;
}

export interface OnboardingStatus {
  steps: OnboardingStep[];
  completed_count: number;
  required_count: number;
  ready_to_activate: boolean;
  activated: boolean;
}

export interface ApiKeySummary {
  id: number;
  name: string;
  key_prefix: string;
  key_type: string;
  scopes: string[];
  allowed_origins: string[];
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface MetaChannelStatus {
  channel_id: number;
  channel_type: Exclude<ChannelType, "webchat" | "whatsapp">;
  mode: "demo" | "live";
  display_name: string;
  configured: boolean;
  is_active: boolean;
  masked_account_id: string | null;
  permissions: string[];
  missing_permissions: string[];
  token_expires_at: string | null;
  token_expiring: boolean;
  webhook_path: string;
}

export interface MetaAccountOption {
  page_id: string;
  page_name: string;
  instagram_account_id: string | null;
  instagram_username: string | null;
}

export interface ShopifyOAuthStart {
  authorization_url: string;
  state: string;
  shop: string;
}
