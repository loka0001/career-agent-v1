import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type { ContentItem } from "../../lib/types";
import { CampaignCalendarPage, moveCalendarDate } from "./CampaignCalendarPage";

const event = (id: number, date: string): ContentItem => ({
  id,
  scheduled_for: date,
  title: `Post ${id}`,
  status: "publish_unknown",
  platform: "instagram",
  product_id: "P1",
  campaign_id: null,
  caption: "Caption",
  body: "Facts",
  tone: "",
  content_format: "sales_post",
  hashtags: [],
  cta: "",
  validation_warnings: [],
  current_version: 1,
  published_at: null,
  external_id: null,
  approved_at: null,
  approved_by: null,
  approved_by_user_id: null,
  created_at: date,
  updated_at: date,
});
function show(query = "?view=agenda&date=2026-09-08") {
  return render(
    <MemoryRouter initialEntries={[`/app/calendar${query}`]}>
      <LanguageProvider>
        <CampaignCalendarPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  localStorage.setItem("commerce-language", "en");
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  vi.spyOn(api, "studioContent").mockResolvedValue([
    event(1, "2026-09-08T12:00:00"),
    event(2, "2026-09-15T12:00:00"),
  ]);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("does not skip February when advancing from January 31", () => {
  const next = moveCalendarDate(new Date(2026, 0, 31, 12), "month", 1);
  expect([next.getFullYear(), next.getMonth(), next.getDate()]).toEqual([
    2026, 1, 1,
  ]);
});
it("limits agenda to the displayed week and links real content reviews", async () => {
  show();
  expect(
    (await screen.findByRole("link", { name: "Post 1" })).getAttribute("href"),
  ).toBe("/app/studio?content=1");
  expect(screen.queryByRole("link", { name: "Post 2" })).toBeNull();
  expect(screen.getByText("Publish status unknown")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  expect(screen.getByRole("link", { name: "Post 2" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Post 1" })).toBeNull();
  expect(
    screen.getByRole("link", { name: "New campaign" }).getAttribute("href"),
  ).toBe("/app/studio?tab=campaign");
});
it("exposes overflow items through the agenda instead of inert month controls", async () => {
  vi.mocked(api.studioContent).mockResolvedValue(
    [1, 2, 3, 4].map((id) => event(id, "2026-09-08T12:00:00")),
  );
  show("?view=month&date=2026-09-08");
  await screen.findByRole("link", { name: "Post 1" });
  expect(screen.queryByRole("link", { name: "Post 4" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "+1 View all" }));
  expect(screen.getByRole("link", { name: "Post 4" })).toBeTruthy();
});
it("retries loading without claiming an empty calendar after failure", async () => {
  vi.mocked(api.studioContent).mockRejectedValueOnce(new Error("Offline"));
  show();
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry calendar" }),
  );
  expect(screen.queryByText("No content scheduled in this period")).toBeNull();
  await screen.findByRole("link", { name: "Post 1" });
});
