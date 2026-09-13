import type {
  ProductVariant,
  ProductVariantInput,
  InventoryAdjustmentInput,
  InventoryTransaction,
  ProductUpdateInput,
  ApiErrorBody,
  AnalyticsSnapshot,
  AuthSession,
  AuthUser,
  ApiKeySummary,
  Automation,
  AutomationRun,
  BillingCapabilities,
  BrandProfile,
  Campaign,
  CheckoutLink,
  ContentItem,
  ConversationDetail,
  ConversationStatus,
  ConversationSummary,
  CustomerIntelligence,
  DraftOrderInput,
  DashboardSnapshot,
  DeletionRequest,
  IntegrationStatus,
  MarketingPack,
  MetaAccountOption,
  MetaChannelStatus,
  MessageOut,
  Opportunity,
  OpportunityDashboard,
  OrderRecord,
  OrderStatus,
  OperatorAlert,
  OperatorJob,
  OperatorOverview,
  OperatorStore,
  OnboardingStatus,
  Platform,
  Plan,
  ProductRecord,
  ProviderConnection,
  RetentionPolicy,
  CommerceSyncResult,
  PublishResult,
  SalesResponse,
  ShopifyOAuthStart,
  StoreSettings,
  StoreSettingsInput,
  Subscription,
  MemberRole,
  TeamMember,
  WhatsAppSettings,
  WhatsAppPhoneOption,
  WhatsAppTemplate,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody,
  ) {
    super(body.message);
  }
}

export const AUTH_SESSION_EXPIRED_EVENT = "commerce:auth-session-expired";

const PUBLIC_AUTH_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/verify-email",
  "/api/v1/auth/resend-verification",
  "/api/v1/auth/forgot-password",
  "/api/v1/auth/reset-password",
  "/api/v1/auth/accept-invite",
  "/api/v1/auth/me",
]);

function cookie(name: string): string | null {
  const value = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));
  return value ? decodeURIComponent(value.slice(name.length + 1)) : null;
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const method = (init.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = cookie("commerce_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });
  const payload = (await response.json()) as unknown;
  if (!response.ok) {
    if (response.status === 401 && !PUBLIC_AUTH_PATHS.has(path)) {
      window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
    }
    const fallback: ApiErrorBody = {
      code: "http_error",
      message: "تعذر تنفيذ الطلب.",
      details: {},
      request_id: response.headers.get("X-Request-ID") ?? "unknown",
    };
    const envelope = payload as { error?: ApiErrorBody };
    throw new ApiError(response.status, envelope.error ?? fallback);
  }
  return payload as T;
}

export const api = {
  login: (email: string, password: string, otp?: string) =>
    request<{
      user: AuthUser;
      csrf_token: string;
      is_operator: boolean;
      demo_mode: boolean;
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, otp }),
    }),
  register: (body: {
    organization_name: string;
    store_name: string;
    email: string;
    password: string;
    full_name: string;
  }) =>
    request<{
      verification_required: boolean;
      email: string;
      user: AuthUser | null;
      csrf_token: string | null;
    }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }),
  verifyEmail: (token: string) =>
    request<{ user: AuthUser; csrf_token: string }>(
      "/api/v1/auth/verify-email",
      {
        method: "POST",
        body: JSON.stringify({ token }),
      },
    ),
  resendVerification: (email: string) =>
    request<{ message: string }>("/api/v1/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/api/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  acceptInvite: (token: string, password: string, fullName: string) =>
    request<{ user: AuthUser; csrf_token: string }>(
      "/api/v1/auth/accept-invite",
      {
        method: "POST",
        body: JSON.stringify({ token, password, full_name: fullName }),
      },
    ),
  me: () =>
    request<{
      user: AuthUser;
      csrf_token: string;
      is_operator: boolean;
      demo_mode: boolean;
    }>("/api/v1/auth/me"),
  logout: () =>
    request<{ message: string }>("/api/v1/auth/logout", { method: "POST" }),
  sessions: () => request<AuthSession[]>("/api/v1/auth/sessions"),
  revokeSession: (sessionId: string) =>
    request<{ message: string }>(
      `/api/v1/auth/sessions/${encodeURIComponent(sessionId)}/revoke`,
      { method: "POST" },
    ),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ message: string }>("/api/v1/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),
  setupMfa: () =>
    request<{ secret: string; otpauth_uri: string }>("/api/v1/auth/mfa/setup", {
      method: "POST",
    }),
  confirmMfa: (code: string) =>
    request<{ message: string }>("/api/v1/auth/mfa/confirm", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  disableMfa: (password: string, code: string) =>
    request<{ message: string }>("/api/v1/auth/mfa/disable", {
      method: "POST",
      body: JSON.stringify({ password, code }),
    }),
  products: () => request<ProductRecord[]>("/api/v1/products"),
  productVariants: (id: string) =>
    request<ProductVariant[]>(
      `/api/v1/products/${encodeURIComponent(id)}/variants`,
    ),
  createProductVariant: (id: string, body: ProductVariantInput) =>
    request<ProductVariant>(
      `/api/v1/products/${encodeURIComponent(id)}/variants`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  adjustInventory: (id: string, body: InventoryAdjustmentInput) =>
    request<InventoryTransaction>(
      `/api/v1/products/${encodeURIComponent(id)}/inventory/adjust`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  inventoryHistory: (id: string) =>
    request<InventoryTransaction[]>(
      `/api/v1/products/${encodeURIComponent(id)}/inventory/transactions`,
    ),
  product: (id: string) =>
    request<ProductRecord>(`/api/v1/products/${encodeURIComponent(id)}`),
  onboard: (form: FormData) =>
    request<ProductRecord>("/api/v1/products/onboard", {
      method: "POST",
      body: form,
    }),
  review: (id: string, body: ProductUpdateInput) =>
    request<ProductRecord>(`/api/v1/products/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  activate: (id: string) =>
    request<ProductRecord>(
      `/api/v1/products/${encodeURIComponent(id)}/activate`,
      { method: "POST" },
    ),
  generatePack: (id: string) =>
    request<MarketingPack>(
      `/api/v1/products/${encodeURIComponent(id)}/marketing-packs`,
      { method: "POST" },
    ),
  updatePack: (id: number, body: Partial<MarketingPack>) =>
    request<MarketingPack>(`/api/v1/marketing-packs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  approvePack: (id: number) =>
    request<MarketingPack>(`/api/v1/marketing-packs/${id}/approve`, {
      method: "POST",
    }),
  publish: (id: number, platforms: Platform[], key: string) =>
    request<{ results: PublishResult[] }>(
      `/api/v1/marketing-packs/${id}/publish`,
      {
        method: "POST",
        headers: { "Idempotency-Key": key },
        body: JSON.stringify({ platforms }),
      },
    ),
  sales: (message: string) =>
    request<SalesResponse>("/api/v1/sales/assist", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  dashboard: () => request<DashboardSnapshot>("/api/v1/dashboard"),
  conversations: (
    params: {
      status?: ConversationStatus | "";
      q?: string;
      overdue?: boolean;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status_filter", params.status);
    if (params.q) query.set("q", params.q);
    if (params.overdue) query.set("overdue", "true");
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<{
      conversations: ConversationSummary[];
      demo_available: boolean;
    }>(`/api/v1/inbox/conversations${suffix}`);
  },
  conversation: (id: number) =>
    request<ConversationDetail>(`/api/v1/inbox/conversations/${id}`),
  replyConversation: (id: number, text: string, idempotencyKey: string) =>
    request<MessageOut>(`/api/v1/inbox/conversations/${id}/reply`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ text }),
    }),
  sendWhatsAppMedia: (id: number, media: File, caption: string) => {
    const body = new FormData();
    body.set("media", media);
    body.set("caption", caption);
    return request<MessageOut>(
      `/api/v1/integrations/whatsapp/conversations/${id}/media`,
      { method: "POST", body },
    );
  },
  suggestReply: (id: number) =>
    request<SalesResponse>(`/api/v1/inbox/conversations/${id}/suggest`, {
      method: "POST",
    }),
  updateConversation: (
    id: number,
    body: { status?: ConversationStatus; priority?: string; tags?: string[] },
  ) =>
    request<ConversationDetail>(`/api/v1/inbox/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  addNote: (id: number, text: string) =>
    request<MessageOut>(`/api/v1/inbox/conversations/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  simulateInbound: (text: string, customerName: string) =>
    request<ConversationDetail>("/api/v1/inbox/simulate", {
      method: "POST",
      body: JSON.stringify({ text, customer_name: customerName }),
    }),
  integrations: () =>
    request<{ integrations: IntegrationStatus[] }>("/api/v1/integrations"),
  providerConnections: () =>
    request<ProviderConnection[]>("/api/v1/integrations/connections"),
  checkProviderConnection: (id: string) =>
    request<ProviderConnection>(
      `/api/v1/integrations/connections/${id}/check`,
      {
        method: "POST",
      },
    ),
  disconnectProviderConnection: (id: string) =>
    request<ProviderConnection>(
      `/api/v1/integrations/connections/${id}/disconnect`,
      { method: "POST" },
    ),
  connectCommerce: (body: {
    provider: "shopify" | "woocommerce" | "generic_website";
    display_name: string;
    store_url: string;
    access_token: string;
    consumer_key: string;
    consumer_secret: string;
    webhook_secret: string;
    install_webhooks: boolean;
  }) =>
    request<ProviderConnection>("/api/v1/integrations/commerce", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  syncCommerce: (id: string) =>
    request<CommerceSyncResult>(`/api/v1/integrations/commerce/${id}/sync`, {
      method: "POST",
    }),
  startShopifyOAuth: (body: {
    display_name: string;
    shop: string;
    install_webhooks: boolean;
  }) =>
    request<ShopifyOAuthStart>(
      "/api/v1/integrations/commerce/shopify/oauth/start",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),
  exchangeShopifyOAuth: (body: {
    code: string;
    state: string;
    shop: string;
    hmac: string;
    timestamp: string;
    host: string | null;
  }) =>
    request<ProviderConnection>(
      "/api/v1/integrations/commerce/shopify/oauth/exchange",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),
  checkMeta: () =>
    request<{ integrations: IntegrationStatus[] }>(
      "/api/v1/integrations/meta/check",
      { method: "POST" },
    ),
  whatsappSettings: () =>
    request<WhatsAppSettings>("/api/v1/integrations/whatsapp"),
  startWhatsAppEmbedded: () =>
    request<{
      app_id: string;
      config_id: string;
      api_version: string;
      state: string;
      solution_id: string | null;
    }>("/api/v1/integrations/whatsapp/embedded/start", { method: "POST" }),
  exchangeWhatsAppEmbedded: (
    code: string,
    state: string,
    wabaId: string | null,
  ) =>
    request<{ transaction_id: string; phones: WhatsAppPhoneOption[] }>(
      "/api/v1/integrations/whatsapp/embedded/exchange",
      {
        method: "POST",
        body: JSON.stringify({ code, state, waba_id: wabaId }),
      },
    ),
  connectWhatsAppEmbedded: (
    transactionId: string,
    phoneNumberId: string,
    wabaId: string,
    registrationPin: string | null,
  ) =>
    request<WhatsAppSettings>(
      "/api/v1/integrations/whatsapp/embedded/connect",
      {
        method: "POST",
        body: JSON.stringify({
          transaction_id: transactionId,
          phone_number_id: phoneNumberId,
          waba_id: wabaId,
          registration_pin: registrationPin,
        }),
      },
    ),
  saveWhatsAppSettings: (body: {
    mode: "demo" | "live";
    display_name: string;
    phone_number_id: string;
    waba_id: string;
    access_token: string;
    app_secret: string;
    verify_token: string;
    is_active: boolean;
  }) =>
    request<WhatsAppSettings>("/api/v1/integrations/whatsapp", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  checkWhatsApp: () =>
    request<{ success: boolean; error_code: string | null }>(
      "/api/v1/integrations/whatsapp/check",
      { method: "POST" },
    ),
  whatsappTemplates: () =>
    request<WhatsAppTemplate[]>("/api/v1/integrations/whatsapp/templates"),
  syncWhatsAppTemplates: () =>
    request<WhatsAppTemplate[]>(
      "/api/v1/integrations/whatsapp/templates/sync",
      {
        method: "POST",
      },
    ),
  createWhatsAppTemplate: (body: {
    name: string;
    language: string;
    body: string;
    variables: string[];
    category: WhatsAppTemplate["category"];
  }) =>
    request<WhatsAppTemplate>("/api/v1/integrations/whatsapp/templates", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  opportunityDashboard: () =>
    request<OpportunityDashboard>("/api/v1/opportunities/dashboard"),
  opportunities: () => request<Opportunity[]>("/api/v1/opportunities"),
  scanOpportunities: () =>
    request<{ message: string }>("/api/v1/opportunities/scan", {
      method: "POST",
    }),
  decideOpportunity: (
    id: number,
    decision: "approve" | "execute" | "reject" | "won",
    realizedRevenue = "0",
  ) =>
    request<Opportunity>(`/api/v1/opportunities/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, realized_revenue: realizedRevenue }),
    }),
  customers: () => request<CustomerIntelligence[]>("/api/v1/customers"),
  customer: (id: number) =>
    request<CustomerIntelligence>(`/api/v1/customers/${id}`),
  orders: () => request<OrderRecord[]>("/api/v1/orders"),
  createOrder: (body: DraftOrderInput) =>
    request<OrderRecord>("/api/v1/orders", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  transitionOrder: (id: number, status: OrderStatus, notifyCustomer: boolean) =>
    request<OrderRecord>(`/api/v1/orders/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({
        status,
        reason: "Updated from operations workspace",
        notify_customer: notifyCustomer,
      }),
    }),
  checkoutOrder: (id: number) =>
    request<CheckoutLink>(`/api/v1/orders/${id}/checkout`, { method: "POST" }),
  brand: () => request<BrandProfile>("/api/v1/studio/brand"),
  saveBrand: (body: Omit<BrandProfile, "updated_at">) =>
    request<BrandProfile>("/api/v1/studio/brand", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  studioContent: () => request<ContentItem[]>("/api/v1/studio/content"),
  generateContent: (body: {
    product_id: string;
    content_format: string;
    platform: Platform;
    tone: string;
    scheduled_for: string | null;
  }) =>
    request<ContentItem>("/api/v1/studio/content/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  editContent: (id: number, body: Partial<ContentItem>) =>
    request<ContentItem>(`/api/v1/studio/content/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  regenerateContent: (id: number, section: string) =>
    request<ContentItem>(`/api/v1/studio/content/${id}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ section }),
    }),
  approveContent: (id: number) =>
    request<ContentItem>(`/api/v1/studio/content/${id}/approve`, {
      method: "POST",
    }),
  publishContent: (id: number) =>
    request<{ message: string }>(`/api/v1/studio/content/${id}/publish`, {
      method: "POST",
    }),
  generateCampaign: (body: {
    name: string;
    goal: string;
    budget: string;
    product_ids: string[];
    audience: string;
    offer: string;
  }) =>
    request<Campaign>("/api/v1/studio/campaigns/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analytics: (channel = "") => {
    const query = channel ? `?channel=${encodeURIComponent(channel)}` : "";
    return request<AnalyticsSnapshot>(`/api/v1/analytics${query}`);
  },
  automations: () => request<Automation[]>("/api/v1/automations"),
  automationRuns: () => request<AutomationRun[]>("/api/v1/automations/runs"),
  automationTemplates: () =>
    request<{ key: string; name: string }[]>("/api/v1/automations/templates"),
  installAutomationTemplate: (key: string) =>
    request<Automation>(
      `/api/v1/automations/templates/${encodeURIComponent(key)}`,
      {
        method: "POST",
      },
    ),
  setAutomationEnabled: (id: number, enabled: boolean) =>
    request<Automation>(
      `/api/v1/automations/${id}/${enabled ? "enable" : "disable"}`,
      {
        method: "POST",
      },
    ),
  plans: () => request<Plan[]>("/api/v1/billing/plans"),
  subscription: () => request<Subscription>("/api/v1/billing/subscription"),
  billingCapabilities: () =>
    request<BillingCapabilities>("/api/v1/billing/capabilities"),
  changePlan: (planKey: Plan["key"]) =>
    request<Subscription | CheckoutLink>("/api/v1/billing/subscription", {
      method: "POST",
      body: JSON.stringify({ plan_key: planKey }),
    }),
  billingPortal: () =>
    request<CheckoutLink>("/api/v1/billing/portal", { method: "POST" }),
  team: () => request<TeamMember[]>("/api/v1/team"),
  inviteMember: (body: {
    email: string;
    full_name: string;
    role: MemberRole;
  }) =>
    request<{
      invite_id: string;
      email: string;
      role: MemberRole;
      status: string;
      expires_at: string;
    }>("/api/v1/team", { method: "POST", body: JSON.stringify(body) }),
  updateMemberRole: (id: number, role: MemberRole) =>
    request<TeamMember>(`/api/v1/team/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  revokeMember: (id: number) =>
    request<{ message: string }>(`/api/v1/team/${id}/revoke`, {
      method: "POST",
    }),
  storeSettings: () => request<StoreSettings>("/api/v1/settings/store"),
  saveStoreSettings: (body: StoreSettingsInput) =>
    request<StoreSettings>("/api/v1/settings/store", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  privacyExport: () =>
    request<Record<string, unknown>>("/api/v1/privacy/export"),
  retentionPolicy: () => request<RetentionPolicy>("/api/v1/privacy/retention"),
  saveRetentionPolicy: (body: {
    message_days: number;
    media_days: number;
    event_days: number;
  }) =>
    request<RetentionPolicy>("/api/v1/privacy/retention", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  requestAccountDeletion: (password: string) =>
    request<DeletionRequest>("/api/v1/privacy/account-deletion", {
      method: "POST",
      body: JSON.stringify({ password, confirmation: "DELETE" }),
    }),
  requestStoreDeletion: (password: string) =>
    request<DeletionRequest>("/api/v1/privacy/store-deletion", {
      method: "POST",
      body: JSON.stringify({ password, confirmation: "DELETE" }),
    }),
  onboarding: () => request<OnboardingStatus>("/api/v1/settings/onboarding"),
  activateStore: () =>
    request<OnboardingStatus>("/api/v1/settings/onboarding/activate", {
      method: "POST",
    }),
  apiKeys: () => request<ApiKeySummary[]>("/api/v1/api-keys"),
  createApiKey: (name: string, allowedOrigins: string[]) =>
    request<{ key: string; api_key: ApiKeySummary }>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({ name, allowed_origins: allowedOrigins }),
    }),
  revokeApiKey: (id: number) =>
    request<ApiKeySummary>(`/api/v1/api-keys/${id}/revoke`, { method: "POST" }),
  metaChannels: () =>
    request<MetaChannelStatus[]>("/api/v1/integrations/meta/channels"),
  startMetaOAuth: () =>
    request<{ authorization_url: string; state: string; demo: boolean }>(
      "/api/v1/integrations/meta/channels/oauth/start",
      { method: "POST" },
    ),
  exchangeMetaOAuth: (code: string, state: string) =>
    request<{ transaction_id: string; accounts: MetaAccountOption[] }>(
      "/api/v1/integrations/meta/channels/oauth/exchange",
      { method: "POST", body: JSON.stringify({ code, state }) },
    ),
  connectMetaOAuth: (
    transactionId: string,
    pageId: string,
    instagramAccountId: string | null,
  ) =>
    request<MetaChannelStatus[]>(
      "/api/v1/integrations/meta/channels/oauth/connect",
      {
        method: "POST",
        body: JSON.stringify({
          transaction_id: transactionId,
          page_id: pageId,
          instagram_account_id: instagramAccountId,
        }),
      },
    ),
  saveMetaChannel: (
    channelType: MetaChannelStatus["channel_type"],
    body: {
      channel_type: MetaChannelStatus["channel_type"];
      mode: "demo" | "live";
      display_name: string;
      account_id: string;
      access_token: string;
      app_secret: string;
      verify_token: string;
      permissions: string[];
      token_expires_at: string | null;
      is_active: boolean;
    },
  ) =>
    request<MetaChannelStatus>(
      `/api/v1/integrations/meta/channels/${channelType}`,
      { method: "PUT", body: JSON.stringify(body) },
    ),
  checkMetaChannel: (id: number) =>
    request<{ success: boolean; error_code: string | null }>(
      `/api/v1/integrations/meta/channels/${id}/check`,
      { method: "POST" },
    ),
  operatorOverview: () =>
    request<OperatorOverview>("/api/v1/operator/overview"),
  operatorAlerts: () =>
    request<{ generated_at: string; alerts: OperatorAlert[] }>(
      "/api/v1/operator/alerts",
    ),
  operatorStores: (query = "") =>
    request<OperatorStore[]>(
      `/api/v1/operator/stores?query=${encodeURIComponent(query)}`,
    ),
  operatorJobs: () =>
    request<OperatorJob[]>("/api/v1/operator/jobs?status=dead"),
  replayOperatorJob: (id: number) =>
    request<{ status: string; job_id: number }>(
      `/api/v1/operator/jobs/${id}/replay`,
      { method: "POST" },
    ),
  suspendOperatorStore: (id: string, suspended: boolean, reason: string) =>
    request<{ store_id: string; status: string }>(
      `/api/v1/operator/stores/${encodeURIComponent(id)}/suspension`,
      {
        method: "PATCH",
        body: JSON.stringify({ suspended, reason }),
      },
    ),
};
