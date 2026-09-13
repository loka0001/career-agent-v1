import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type { ContentItem } from "../../lib/types";
import { ContentStudioPage } from "./ContentStudioPage";
import { useAuth } from "../../app/AuthContext";
vi.mock("../../app/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { role: "owner" } })),
}));

const item: ContentItem = {
  id: 1,
  campaign_id: null,
  product_id: "P1",
  content_format: "sales_post",
  platform: "instagram",
  tone: "friendly",
  title: "Review this post",
  body: "Facts",
  caption: "Original caption",
  hashtags: [],
  cta: "Read more",
  validation_warnings: [],
  status: "draft",
  current_version: 1,
  scheduled_for: null,
  published_at: null,
  external_id: null,
  approved_at: null,
  approved_by: null,
  approved_by_user_id: null,
  created_at: "2026-09-08T00:00:00Z",
  updated_at: "2026-09-08T00:00:00Z",
};
function show(query = "?view=cards") {
  return render(
    <MemoryRouter initialEntries={[`/app/studio${query}`]}>
      <LanguageProvider>
        <ContentStudioPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({ user: { role: "owner" } } as ReturnType<
    typeof useAuth
  >);
  localStorage.setItem("commerce-language", "en");
  vi.spyOn(api, "studioContent").mockResolvedValue([item]);
  vi.spyOn(api, "products").mockResolvedValue([]);
  vi.spyOn(api, "brand").mockResolvedValue({
    tone: "friendly",
    audience: "",
    guidelines: "",
    primary_color: "#123456",
    updated_at: item.updated_at,
  });
});
afterEach(() => vi.restoreAllMocks());

it("opens the campaign builder from a Calendar link", async () => {
  show("?tab=campaign");
  await screen.findByLabelText("Campaign name");
  expect(screen.getByRole("button", { name: "Build campaign" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Generate draft" })).toBeNull();
});

it("keeps the queue visible until the merchant deliberately opens the draft creator", async () => {
  show("");
  await screen.findByRole("link", { name: item.title });
  expect(screen.queryByRole("button", { name: "Generate draft" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Create draft" }));
  expect(screen.getByRole("button", { name: "Generate draft" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("button", { name: "Generate draft" })).toBeNull();
  expect(screen.getByRole("list", { name: "Review queue" })).toBeTruthy();
});

it("defaults to a compact queue and retains unsaved edits across review navigation", async () => {
  show("");
  const link = await screen.findByRole("link", { name: item.title });
  expect(screen.queryByLabelText("Caption 1")).toBeNull();
  expect(screen.getByRole("list", { name: "Review queue" })).toBeTruthy();
  fireEvent.click(link);
  fireEvent.change(screen.getByLabelText("Caption 1"), {
    target: { value: "Pending revision" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Back to content list" }));
  expect(screen.getByText("Unsaved changes")).toBeTruthy();
  expect(screen.getByText("Pending revision")).toBeTruthy();
  fireEvent.click(screen.getByRole("link", { name: item.title }));
  expect(screen.getByDisplayValue("Pending revision")).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Approve" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});

it("switches between queue and editors without losing filters", async () => {
  show("?q=Review&status=draft");
  await screen.findByRole("link", { name: item.title });
  fireEvent.click(screen.getByRole("button", { name: "Post editors" }));
  expect(screen.getByLabelText("Caption 1")).toBeTruthy();
  expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe(
    "Review",
  );
  fireEvent.click(screen.getByRole("button", { name: "Review queue" }));
  expect(screen.queryByLabelText("Caption 1")).toBeNull();
  expect(
    (screen.getByLabelText("Content status") as HTMLSelectElement).value,
  ).toBe("draft");
});

it("preserves available content when brand fails and retries only the unavailable source", async () => {
  vi.mocked(api.brand).mockRejectedValueOnce(new Error("Brand unavailable"));
  show();
  const caption = await screen.findByLabelText("Caption 1");
  fireEvent.change(caption, { target: { value: "Unsaved merchant text" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Retry unavailable sections" }),
  );
  await screen.findByDisplayValue("Unsaved merchant text");
  expect(api.studioContent).toHaveBeenCalledTimes(1);
  expect(api.products).toHaveBeenCalledTimes(1);
  expect(api.brand).toHaveBeenCalledTimes(2);
});

it("does not mislabel failed content loading as an empty library", async () => {
  vi.mocked(api.studioContent).mockRejectedValueOnce(new Error("Offline"));
  show();
  await screen.findByRole("button", { name: "Retry unavailable sections" });
  expect(screen.queryByText("No drafts yet")).toBeNull();
});

it("filters content and preserves filters across review links", async () => {
  show();
  const link = await screen.findByRole("link", { name: item.title });
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Review" },
  });
  fireEvent.change(screen.getByLabelText("Content status"), {
    target: { value: "draft" },
  });
  expect(link.getAttribute("href")).toContain(
    "q=Review&status=draft&content=1",
  );
  fireEvent.click(link);
  expect(screen.queryByRole("searchbox")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Back to content list" }));
  expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe(
    "Review",
  );
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "absent" },
  });
  expect(screen.getByText("No content matches these filters.")).toBeTruthy();
});

it("keeps analyst controls read-only while allowing status refresh", async () => {
  const current = useAuth();
  vi.mocked(useAuth).mockReturnValueOnce({
    ...current,
    user: { ...current.user!, role: "analyst" },
  });
  // Keep the role stable across loading and query state renders.
  vi.mocked(useAuth).mockReturnValue({
    ...current,
    user: { ...current.user!, role: "analyst" },
  });
  show();
  expect(
    ((await screen.findByLabelText("Caption 1")) as HTMLTextAreaElement)
      .disabled,
  ).toBe(true);
  expect(screen.queryByRole("button", { name: "Generate draft" })).toBeNull();
  expect(
    (screen.getByRole("button", { name: "Approve" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(
    (
      screen.getByRole("button", {
        name: "Refresh delivery status",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("refreshes delivery without losing unsaved captions and preserves items on refresh failure", async () => {
  show();
  fireEvent.change(await screen.findByLabelText("Caption 1"), {
    target: { value: "Local draft" },
  });
  vi.mocked(api.studioContent).mockResolvedValueOnce([
    { ...item, status: "approved" },
  ]);
  fireEvent.click(
    screen.getByRole("button", { name: "Refresh delivery status" }),
  );
  await screen.findByText("Approved");
  expect(screen.getByDisplayValue("Local draft")).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Publish" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  vi.mocked(api.studioContent).mockRejectedValueOnce(new Error("Offline"));
  fireEvent.click(
    screen.getByRole("button", { name: "Refresh delivery status" }),
  );
  await screen.findByText("Data could not be loaded. Try again.");
  expect(screen.getByDisplayValue("Local draft")).toBeTruthy();
});

it("requires saving the visible caption before approval and shows regenerated server text", async () => {
  vi.spyOn(api, "editContent").mockResolvedValue({
    ...item,
    caption: "Merchant edit",
    current_version: 2,
  });
  vi.spyOn(api, "regenerateContent").mockResolvedValue({
    ...item,
    caption: "Regenerated caption",
    current_version: 3,
  });
  show();
  const caption = await screen.findByLabelText("Caption 1");
  fireEvent.change(caption, { target: { value: "Merchant edit" } });
  expect(
    (
      screen.getByRole("button", {
        name: "Approve",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(
    (
      screen.getByRole("button", {
        name: "Regenerate caption",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await screen.findByText("save completed.");
  expect(api.editContent).toHaveBeenCalledWith(1, { caption: "Merchant edit" });
  expect(
    (
      screen.getByRole("button", {
        name: "Approve",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Regenerate caption" }));
  await screen.findByDisplayValue("Regenerated caption");
  expect(api.studioContent).toHaveBeenCalledTimes(1);
});

it("preserves failed edits and blocks publishing until changes are discarded", async () => {
  vi.mocked(api.studioContent).mockResolvedValue([
    { ...item, status: "approved" },
  ]);
  vi.spyOn(api, "editContent").mockRejectedValue(new Error("Save unavailable"));
  show();
  fireEvent.change(await screen.findByLabelText("Caption 1"), {
    target: { value: "Unsaved" },
  });
  expect(
    (
      screen.getByRole("button", {
        name: "Publish",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await screen.findByText("Data could not be loaded. Try again.");
  expect(screen.getByDisplayValue("Unsaved")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(screen.getByDisplayValue("Original caption")).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Publish",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it.each(["published", "publishing", "publish_retrying", "publish_unknown"])(
  "keeps %s content immutable",
  async (status) => {
    vi.mocked(api.studioContent).mockResolvedValue([{ ...item, status }]);
    show();
    expect(
      ((await screen.findByLabelText("Caption 1")) as HTMLTextAreaElement)
        .disabled,
    ).toBe(true);
    expect(
      (
        screen.getByRole("button", {
          name: "Regenerate caption",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  },
);
