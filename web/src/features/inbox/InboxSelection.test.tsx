import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type {
  ConversationDetail,
  CustomerIntelligence,
  SalesResponse,
} from "../../lib/types";
import { CustomersPage } from "../customers/CustomersPage";
import { InboxPage } from "./InboxPage";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function conversation(id: number, name: string): ConversationDetail {
  return {
    id,
    channel_type: "webchat",
    status: "open",
    priority: "normal",
    customer: {
      id,
      display_name: name,
      phone: null,
      email: null,
      tags: [],
      lead_score: 20,
      consent: {},
      first_seen_at: "2026-09-01T10:00:00Z",
      last_seen_at: "2026-09-07T10:00:00Z",
    },
    assignee_user_id: null,
    last_message_preview: `Message from ${name}`,
    unread_count: 1,
    tags: [],
    sla_overdue: false,
    last_inbound_at: null,
    last_outbound_at: null,
    updated_at: "2026-09-07T10:00:00Z",
    messages: [],
  };
}

const first = conversation(1, "Mona");
const second = conversation(2, "Ali");

function intelligence(detail: ConversationDetail): CustomerIntelligence {
  return {
    customer: detail.customer,
    lead_score: 20,
    score_signals: [],
    segments: ["new"],
    completed_orders: 0,
    total_revenue: "0",
    average_order_value: "0",
    days_since_last_activity: 0,
    preferred_product_ids: [],
    rfm: {
      recency_days: 0,
      frequency: 0,
      monetary: "0",
      recency_score: 5,
      frequency_score: 1,
      monetary_score: 1,
    },
    purchase_probability: 20,
    churn_risk: "low",
    timeline: [],
  };
}

const suggestion: SalesResponse = {
  need: {
    intent: "product_search",
    categories: [],
    max_budget: null,
    required_features: [],
    use_cases: [],
    excluded_features: [],
    language: "en",
  },
  recommendations: [],
  reply: "Reply intended for Mona",
  citations: [],
  insufficient_context: false,
};

function renderInbox() {
  return render(
    <MemoryRouter>
      <LanguageProvider>
        <InboxPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}

function choose(name: string) {
  fireEvent.click(
    screen.getByRole("button", { name: new RegExp(`^${name}.*Message from`) }),
  );
}

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "scrollTo", {
    configurable: true,
    value: vi.fn(),
  });
});
afterAll(() => {
  Reflect.deleteProperty(HTMLElement.prototype, "scrollTo");
});

beforeEach(() => {
  localStorage.setItem("commerce-language", "en");
  vi.spyOn(api, "conversations").mockResolvedValue({
    conversations: [first, second],
    demo_available: false,
  });
  vi.spyOn(api, "conversation").mockImplementation(async (id) =>
    id === 1 ? first : second,
  );
  vi.spyOn(api, "customer").mockImplementation(async (id) =>
    intelligence(id === 1 ? first : second),
  );
  vi.spyOn(api, "orders").mockResolvedValue([]);
  vi.spyOn(HTMLElement.prototype, "scrollTo").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("keeps the latest selected conversation when detail responses arrive out of order", async () => {
  const slow = deferred<ConversationDetail>();
  vi.mocked(api.conversation).mockImplementation((id) =>
    id === 1 ? slow.promise : Promise.resolve(second),
  );
  renderInbox();
  await screen.findByText("Message from Mona");
  choose("Mona");
  choose("Ali");
  await screen.findByRole("heading", { name: "Ali" });
  await act(async () => slow.resolve(first));
  expect(screen.queryByRole("heading", { name: "Mona" })).toBeNull();
  expect(screen.getByRole("heading", { name: "Ali" })).toBeTruthy();
});

it("does not copy a pending suggestion into another customer's composer", async () => {
  const slow = deferred<SalesResponse>();
  vi.spyOn(api, "suggestReply").mockReturnValue(slow.promise);
  renderInbox();
  await screen.findByText("Message from Mona");
  choose("Mona");
  await screen.findByRole("heading", { name: "Mona" });
  fireEvent.click(screen.getByRole("button", { name: "Smart suggestion" }));
  choose("Ali");
  await screen.findByRole("heading", { name: "Ali" });
  fireEvent.change(screen.getByRole("textbox", { name: "Reply text" }), {
    target: { value: "Ali's own draft" },
  });
  await act(async () => slow.resolve(suggestion));
  expect(
    (screen.getByRole("textbox", { name: "Reply text" }) as HTMLTextAreaElement)
      .value,
  ).toBe("Ali's own draft");
  expect(screen.queryByText(/This suggestion is grounded/)).toBeNull();
});

it("does not navigate back when a queued reply receives its delayed delivery refresh", async () => {
  vi.spyOn(api, "replyConversation").mockResolvedValue({
    id: 99,
    direction: "outbound",
    sender_type: "agent",
    body: "Hello Mona",
    attachments: [],
    status: "queued",
    external_id: null,
    error_message: null,
    created_at: "2026-09-07T10:00:00Z",
  });
  renderInbox();
  await screen.findByText("Message from Mona");
  choose("Mona");
  await screen.findByRole("heading", { name: "Mona" });
  vi.useFakeTimers();
  fireEvent.change(screen.getByRole("textbox", { name: "Reply text" }), {
    target: { value: "Hello Mona" },
  });
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Send" })),
  );
  await act(async () => choose("Ali"));
  fireEvent.change(screen.getByRole("textbox", { name: "Reply text" }), {
    target: { value: "Ali's draft" },
  });
  await act(async () => vi.advanceTimersByTimeAsync(1500));
  expect(screen.getByRole("heading", { name: "Ali" })).toBeTruthy();
  expect(
    (screen.getByRole("textbox", { name: "Reply text" }) as HTMLTextAreaElement)
      .value,
  ).toBe("Ali's draft");
});

it("invalidates old customer context as soon as another conversation is selected", async () => {
  const oldContext = deferred<CustomerIntelligence>();
  const newDetail = deferred<ConversationDetail>();
  vi.mocked(api.customer).mockImplementation((id) =>
    id === 1 ? oldContext.promise : Promise.resolve(intelligence(second)),
  );
  vi.mocked(api.conversation).mockImplementation((id) =>
    id === 1 ? Promise.resolve(first) : newDetail.promise,
  );
  const { container } = renderInbox();
  await screen.findByText("Message from Mona");
  choose("Mona");
  await screen.findByRole("heading", { name: "Mona" });
  choose("Ali");
  await act(async () => oldContext.resolve(intelligence(first)));
  expect(container.querySelector(".inbox-context")?.textContent).not.toContain(
    "Mona",
  );
  await act(async () => newDetail.resolve(second));
  await waitFor(() =>
    expect(container.querySelector(".inbox-context")?.textContent).toContain(
      "Ali",
    ),
  );
});

it("distinguishes unavailable orders from empty orders and can retry context", async () => {
  vi.mocked(api.orders).mockRejectedValueOnce(
    new Error("temporarily unavailable"),
  );
  const { container } = renderInbox();
  await screen.findByText("Message from Mona");
  choose("Mona");
  await screen.findByText(
    "Some customer or order context could not be loaded.",
  );
  expect(screen.queryByText(/No orders are linked/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry context" }));
  await waitFor(() => expect(api.orders).toHaveBeenCalledTimes(2));
  await waitFor(() =>
    expect(
      within(
        container.querySelector(".inbox-context") as HTMLElement,
      ).queryByRole("button", { name: "Retry context" }),
    ).toBeNull(),
  );
});

it("opens the customer from an Inbox profile link instead of the first customer", async () => {
  vi.spyOn(api, "customers").mockResolvedValue([
    intelligence(first),
    intelligence(second),
  ]);
  render(
    <MemoryRouter initialEntries={["/app/customers?customer=2"]}>
      <LanguageProvider>
        <CustomersPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
  expect(await screen.findByRole("heading", { name: "Ali" })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Mona" })).toBeNull();
});

it("does not silently substitute a customer when a linked profile is unavailable", async () => {
  vi.spyOn(api, "customers").mockResolvedValue([intelligence(first)]);
  render(
    <MemoryRouter initialEntries={["/app/customers?customer=999"]}>
      <LanguageProvider>
        <CustomersPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
  await screen.findByText("The requested customer is unavailable.");
  expect(screen.queryByRole("heading", { name: "Mona" })).toBeNull();
});
