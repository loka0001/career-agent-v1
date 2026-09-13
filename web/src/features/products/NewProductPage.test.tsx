import { fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type { ProductRecord, MarketingPack } from "../../lib/types";
import { NewProductPage } from "./NewProductPage";

const product = {
  product_id: "P1",
  name: "Headphones",
  category: "Audio",
  price: "25.00",
  stock: 5,
  features: ["Bluetooth"],
  customer_benefits: ["Portable"],
  description: "Wireless headphones",
  status: "draft",
} as ProductRecord;
const pack: MarketingPack = {
  id: 1,
  product_id: "P1",
  facebook_message: "Facebook copy",
  instagram_caption: "Instagram copy",
  hashtags: ["#audio"],
  image_url: "/image.png",
  validation_warnings: [],
  version: 1,
  status: "draft",
  approved_at: null,
  approved_by: null,
  created_at: "2026-09-08T03:00:00Z",
  updated_at: "2026-09-08T03:00:00Z",
};
beforeEach(() => {
  localStorage.setItem("commerce-language", "en");
});
afterEach(() => vi.restoreAllMocks());

it("renders complete English creation fields and a localized retryable failure", async () => {
  vi.spyOn(api, "onboard").mockRejectedValue(new Error("Offline"));
  render(
    <LanguageProvider>
      <NewProductPage />
    </LanguageProvider>,
  );
  for (const label of [
    "Name",
    "Category",
    "Price (EGP)",
    "Stock",
    "Specifications — one per line",
    "JPEG, PNG, or WebP image (maximum 10 MB)",
  ])
    expect(screen.getByLabelText(label)).toBeTruthy();
  fireEvent.submit(screen.getByLabelText("Name").closest("form")!);
  await screen.findByText("An unexpected error occurred. Try this step again.");
});

it("requires saved content before approval and distinguishes demo publication", async () => {
  vi.spyOn(api, "onboard").mockResolvedValue(product);
  vi.spyOn(api, "review").mockResolvedValue({ ...product, status: "reviewed" });
  vi.spyOn(api, "activate").mockResolvedValue({ ...product, status: "active" });
  vi.spyOn(api, "generatePack").mockResolvedValue(pack);
  vi.spyOn(api, "updatePack").mockResolvedValue({
    ...pack,
    facebook_message: "Edited copy",
  });
  vi.spyOn(api, "approvePack").mockResolvedValue({
    ...pack,
    status: "approved",
  });
  vi.spyOn(api, "publish").mockResolvedValue({
    results: [
      {
        publication_id: 1,
        platform: "facebook",
        success: true,
        external_id: "demo-post-1",
        permalink: null,
        error_code: null,
        error_message: null,
        raw_status: "DEMO",
      },
    ],
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(
    <LanguageProvider>
      <NewProductPage />
    </LanguageProvider>,
  );
  fireEvent.submit(screen.getByLabelText("Name").closest("form")!);
  await screen.findByRole("heading", { name: "2. Review extracted facts" });
  fireEvent.click(screen.getByRole("button", { name: "Save and activate" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Create content" }),
  );
  const facebook = await screen.findByLabelText("Facebook text");
  expect(screen.getAllByText("Post preview")).toHaveLength(2);
  fireEvent.change(facebook, { target: { value: "Edited copy" } });
  expect(
    (
      screen.getByRole("button", {
        name: "Explicit approval",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText(
    "Changes saved. Any previous approval has been cleared.",
  );
  fireEvent.click(screen.getByRole("button", { name: "Explicit approval" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Publish to both platforms" }),
  );
  await screen.findByText("Demo completed — no live post was created");
  expect(window.confirm).toHaveBeenCalledWith(
    "Confirm publishing to Facebook and Instagram?",
  );
  expect(api.updatePack).toHaveBeenCalledWith(
    1,
    expect.objectContaining({ facebook_message: "Edited copy" }),
  );
});
