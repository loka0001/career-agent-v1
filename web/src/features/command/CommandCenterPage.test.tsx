import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type {
  ContentItem,
  ConversationSummary,
  ProviderConnection,
} from "../../lib/types";
import { CommandCenterPage } from "./CommandCenterPage";

function customer(id: number, displayName: string) {
  return {
    id,
    display_name: displayName,
    phone: null,
    email: null,
    tags: [],
    lead_score: 50,
    consent: {},
    first_seen_at: "2026-09-06T00:00:00Z",
    last_seen_at: "2026-09-06T00:00:00Z",
  };
}

function conversation(
  id: number,
  displayName: string,
  overrides: Partial<ConversationSummary> = {},
): ConversationSummary {
  return {
    id,
    channel_type: "whatsapp",
    status: "open",
    priority: "normal",
    customer: customer(id, displayName),
    assignee_user_id: null,
    last_message_preview: "",
    unread_count: 0,
    tags: [],
    sla_overdue: false,
    last_inbound_at: "2026-09-06T02:00:00Z",
    last_outbound_at: null,
    updated_at: "2026-09-06T02:00:00Z",
    ...overrides,
  };
}

function content(
  id: number,
  status: string,
  validationWarnings: string[] = [],
): ContentItem {
  return {
    id,
    campaign_id: null,
    product_id: `product-${id}`,
    content_format: "post",
    platform: "instagram",
    tone: "friendly",
    title: `Content ${id}`,
    body: "Body",
    caption: "Caption",
    hashtags: [],
    cta: "Shop now",
    validation_warnings: validationWarnings,
    status,
    current_version: 1,
    scheduled_for: null,
    published_at: status === "published" ? "2026-09-06T02:00:00Z" : null,
    external_id: null,
    approved_at: null,
    approved_by: null,
    approved_by_user_id: null,
    created_at: "2026-09-06T00:00:00Z",
    updated_at: "2026-09-06T02:00:00Z",
  };
}

function connection(connectionType: string): ProviderConnection {
  return {
    id: connectionType,
    provider: "meta",
    connection_type: connectionType,
    mode: "live",
    display_name: connectionType,
    external_account_id: "account",
    external_business_id: "business",
    external_resource_id: "resource",
    scopes: [],
    capabilities: [],
    status: "connected",
    token_expires_at: null,
    token_expiring: false,
    last_health_at: "2026-09-06T02:00:00Z",
    last_successful_sync_at: "2026-09-06T02:00:00Z",
    last_error_code: null,
    created_at: "2026-09-06T00:00:00Z",
    updated_at: "2026-09-06T02:00:00Z",
  };
}

function mockHomeApis() {
  vi.spyOn(api, "conversations").mockResolvedValue({
    demo_available: true,
    conversations: [
      conversation(1, "Amina", { sla_overdue: true, unread_count: 1 }),
      conversation(2, "Omar"),
      conversation(3, "Replied customer", {
        last_inbound_at: "2026-09-06T01:00:00Z",
        last_outbound_at: "2026-09-06T02:00:00Z",
      }),
    ],
  });
  vi.spyOn(api, "studioContent").mockResolvedValue([
    content(1, "draft"),
    content(2, "draft", ["Missing factual support"]),
    content(3, "publish_unknown"),
    content(4, "published"),
  ]);
  vi.spyOn(api, "providerConnections").mockResolvedValue([
    connection("facebook_page"),
  ]);
  vi.spyOn(api, "whatsappSettings").mockResolvedValue({
    channel_id: null,
    mode: "live",
    demo_available: true,
    display_name: "WhatsApp Business",
    configured: false,
    is_active: true,
    masked_phone_number_id: null,
    masked_waba_id: null,
    webhook_path: "/webhooks/whatsapp/demo",
    embedded_signup_available: false,
    connection_status: "disconnected",
  });
  vi.spyOn(api, "orders").mockResolvedValue([]);
  vi.spyOn(api, "analytics").mockResolvedValue({
    period_start: "2026-09-01T00:00:00Z",
    period_end: "2026-09-06T00:00:00Z",
    channel: null,
    conversation_volume: 10,
    first_response_minutes: "4.5",
    resolution_minutes: null,
    leads: 3,
    conversion_rate: "20.0",
    attributed_revenue: "0.00",
    recovered_revenue: "0.00",
    orders_by_channel: {},
    top_products: [],
    content_published: 1,
    content_engagements: 0,
    automation_runs: 0,
    automation_success_rate: "0.0",
    ai_operations: 7,
    ai_cost: null,
    agent_performance: [],
    funnel: {},
  });
}

function statText(label: string): string {
  const card = screen.getByText(label).closest("section");
  expect(card).not.toBeNull();
  return card?.textContent ?? "";
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("CommandCenterPage", () => {
  it("renders a truthful, actionable English home from live API data", async () => {
    localStorage.setItem("commerce-language", "en");
    mockHomeApis();

    render(
      <MemoryRouter>
        <LanguageProvider>
          <CommandCenterPage />
        </LanguageProvider>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Needs attention" }),
      ).toBeTruthy(),
    );
    expect(statText("Conversations awaiting reply")).toContain("2");
    expect(statText("Content awaiting review")).toContain("1");
    expect(statText("Publishing needs attention")).toContain("1");
    expect(statText("Channels requiring setup")).toContain("2");
    expect(screen.getByText("Amina")).toBeTruthy();
    expect(screen.getByText("Omar")).toBeTruthy();
    expect(screen.queryByText("Replied customer")).toBeNull();
    expect(screen.getByText("Recent outcomes")).toBeTruthy();
    expect(screen.getByText("4.5 min")).toBeTruthy();
    expect(screen.queryByText("إيراد محتمل")).toBeNull();
  });

  it("keeps available home sections visible when one source fails", async () => {
    localStorage.setItem("commerce-language", "en");
    mockHomeApis();
    vi.mocked(api.analytics).mockRejectedValueOnce(new Error("Unavailable"));

    render(
      <MemoryRouter>
        <LanguageProvider>
          <CommandCenterPage />
        </LanguageProvider>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(
        screen.getByText(/Some live store data could not be loaded/),
      ).toBeTruthy(),
    );
    expect(screen.getByText(/response time/)).toBeTruthy();
    expect(screen.getByText("Amina")).toBeTruthy();
    expect(statText("Conversations awaiting reply")).toContain("2");
    expect(statText("Average first response")).toContain("Unavailable");
  });
});
