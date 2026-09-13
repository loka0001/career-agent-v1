import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type {
  CustomerIntelligence,
  OrderRecord,
  SalesResponse,
} from "../../lib/types";
import {
  InboxContextRail,
  relatedOrdersForConversation,
} from "./InboxContextRail";
import { inboxCopy } from "./inboxCopy";
import { messageStatusLabel } from "./messageStatus";
import { SuggestionEvidence } from "./SuggestionEvidence";

const groundedSuggestion: SalesResponse = {
  need: {
    intent: "product_search",
    categories: ["Audio"],
    max_budget: "1500.00",
    required_features: ["microphone"],
    use_cases: ["study"],
    excluded_features: [],
    language: "en",
  },
  recommendations: [],
  reply: "A catalog-grounded reply.",
  citations: ["product:P101", "policy:returns"],
  insufficient_context: false,
};

describe("SuggestionEvidence", () => {
  it("provides complete English chrome for the P0 inbox workflow", () => {
    const copy = inboxCopy("en");

    expect(copy).toMatchObject({
      loadError: "Conversations could not be loaded",
      openError: "Conversation could not be opened",
      unexpectedError: "An unexpected error occurred.",
      replyQueued: "The reply is on its way through the channel.",
      mediaQueued: "The file is on its way through WhatsApp.",
      suggestionReady:
        "This suggestion is grounded in store data — review it before sending.",
      demoMessageArrived: "A new demo message arrived.",
      overdue: "Overdue",
      newMessages: "new",
      leadScore: "Lead score",
      attachedImage: "Attached image",
      openDocument: "Open document",
      internalNote: "Internal note",
      suggestedProducts: "Suggested products",
      attachFile: "Attach file",
      sendFile: "Send",
      currency: "EGP",
      contextTitle: "Customer & commerce context",
      recentOrders: "Related orders",
    });
    expect(copy.demoCustomer).toBe("Demo customer");
    expect(copy.examples).toHaveLength(3);
  });

  it("shows real customer intelligence and only related orders in the context rail", () => {
    const customer: CustomerIntelligence = {
      customer: {
        id: 7,
        display_name: "Mona Ali",
        phone: "+201000000000",
        email: null,
        tags: ["VIP"],
        lead_score: 82,
        consent: {},
        first_seen_at: "2026-09-01T10:00:00Z",
        last_seen_at: "2026-09-07T10:00:00Z",
      },
      lead_score: 82,
      score_signals: [],
      segments: ["repeat-buyer"],
      completed_orders: 3,
      total_revenue: "2450.00",
      average_order_value: "816.67",
      days_since_last_activity: 0,
      preferred_product_ids: [],
      rfm: {
        recency_days: 0,
        frequency: 3,
        monetary: "2450.00",
        recency_score: 5,
        frequency_score: 4,
        monetary_score: 4,
      },
      purchase_probability: 76,
      churn_risk: "low",
      timeline: [],
    };
    const order = {
      id: 19,
      customer_id: 7,
      conversation_id: 11,
      status: "paid",
      currency: "EGP",
      subtotal: "850.00",
      discount: "0.00",
      shipping_total: "0.00",
      tax_total: "0.00",
      total: "850.00",
      shipping: {},
      notes: "",
      payment_provider: null,
      payment_status: "paid",
      fulfillment_status: "unfulfilled",
      provider_references: {},
      refunded_amount: "0.00",
      items: [
        {
          product_id: "P101",
          variant_id: null,
          sku: "P101",
          options: {},
          product_name: "Study headphones",
          unit_price: "850.00",
          quantity: 1,
          line_total: "850.00",
        },
      ],
      timeline: [],
      created_at: "2026-09-07T10:00:00Z",
      updated_at: "2026-09-07T10:00:00Z",
    } satisfies OrderRecord;

    expect(
      relatedOrdersForConversation(
        [order, { ...order, id: 20, customer_id: 99, conversation_id: 99 }],
        7,
        11,
      ),
    ).toEqual([order]);

    render(
      <MemoryRouter>
        <InboxContextRail
          fallbackCustomer={customer.customer}
          customer={customer}
          orders={[order]}
          loading={false}
          error=""
          language="en"
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Mona Ali")).toBeTruthy();
    expect(screen.queryByText("EGP 2,450")).toBeNull();
    expect(screen.getByText("850.00 EGP")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Open customer profile" })
        .getAttribute("href"),
    ).toBe("/app/customers?customer=7");
    expect(screen.getByText("Order #19")).toBeTruthy();
    expect(screen.getByText("Study headphones")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "View all orders" })
        .getAttribute("href"),
    ).toBe("/app/orders");
  });

  it("renders order lifecycle tones and an honest empty context state", () => {
    const baseOrder = {
      id: 1,
      customer_id: 7,
      conversation_id: 11,
      status: "draft",
      currency: "EGP",
      subtotal: "0.00",
      discount: "0.00",
      shipping_total: "0.00",
      tax_total: "0.00",
      total: "0.00",
      shipping: {},
      notes: "",
      payment_provider: null,
      payment_status: null,
      fulfillment_status: "unfulfilled",
      provider_references: {},
      refunded_amount: "0.00",
      items: [],
      timeline: [],
      created_at: "2026-09-07T10:00:00Z",
      updated_at: "2026-09-07T10:00:00Z",
    } satisfies OrderRecord;
    const fallbackCustomer = {
      id: 7,
      display_name: "Mona Ali",
      phone: null,
      email: "mona@example.com",
      tags: [],
      lead_score: 50,
      consent: {},
      first_seen_at: "2026-09-01T10:00:00Z",
      last_seen_at: "2026-09-07T10:00:00Z",
    };

    const { rerender } = render(
      <MemoryRouter>
        <InboxContextRail
          fallbackCustomer={fallbackCustomer}
          customer={null}
          orders={[
            baseOrder,
            { ...baseOrder, id: 2, status: "cancelled" },
            { ...baseOrder, id: 3, status: "processing" },
          ]}
          loading={false}
          error=""
          language="en"
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Draft")).toBeTruthy();
    expect(screen.getByText("Cancelled")).toBeTruthy();
    expect(screen.getByText("Processing")).toBeTruthy();

    rerender(
      <MemoryRouter>
        <InboxContextRail
          fallbackCustomer={null}
          customer={null}
          orders={[]}
          loading={false}
          error="Some customer or order context could not be loaded."
          language="en"
        />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(
        "Select a conversation to view customer and order context.",
      ),
    ).toBeTruthy();
  });

  it("shows the grounding citations returned with a sales suggestion", () => {
    render(
      <SuggestionEvidence suggestion={groundedSuggestion} language="en" />,
    );

    const citations = screen.getByLabelText("Grounding citations");
    expect(citations.textContent).toContain("product:P101");
    expect(citations.textContent).toContain("policy:returns");
  });

  it("warns operators to reconcile an ambiguous delivery before resending", () => {
    expect(messageStatusLabel("delivery_unknown", "en")).toBe(
      "Delivery unknown — review the channel before resending",
    );
    expect(messageStatusLabel("delivery_unknown", "ar")).toContain(
      "راجع القناة",
    );
  });

  it("maps every actionable outbound delivery state in both languages", () => {
    expect(messageStatusLabel("sent", "en")).toBe("Sent ✓");
    expect(messageStatusLabel("sent", "ar")).toContain("أُرسلت");
    expect(messageStatusLabel("queued", "en")).toBe("Sending…");
    expect(messageStatusLabel("sending", "ar")).toBe("في الطريق…");
    expect(messageStatusLabel("failed", "en")).toBe("Send failed");
    expect(messageStatusLabel("failed", "ar")).toBe("فشل الإرسال");
    expect(messageStatusLabel("delivered", "en")).toBe("delivered");
  });
});
