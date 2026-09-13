import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type { ProductRecord } from "../../lib/types";
import { ProductDetail, productReviewInput } from "./ProductDetail";
import { ProductsPage } from "./ProductsPage";

vi.mock("../../app/AuthContext", () => ({
  useAuth: () => ({ user: { role: "owner" } }),
}));
const product: ProductRecord = {
  product_id: "P101",
  store_id: "store",
  name: "Study headphones",
  category: "Audio",
  price: "1500.25",
  stock: 8,
  features: ["Bluetooth"],
  customer_benefits: ["Portable"],
  description: "Wireless headphones.",
  image_summary: "Headphones",
  original_image_url: "/placeholder.svg",
  public_image_url: null,
  status: "active",
  currency: "USD",
  source_of_truth: "local",
  created_at: "2026-09-07T10:00:00Z",
  updated_at: "2026-09-07T10:00:00Z",
};
const reviewed = {
  ...product,
  name: "Updated headphones",
  status: "reviewed" as const,
};

function renderDetail(
  props: Partial<Parameters<typeof ProductDetail>[0]> = {},
) {
  return render(
    <ProductDetail
      id={product.product_id}
      language="en"
      canEdit
      onBack={vi.fn()}
      onUpdated={vi.fn()}
      {...props}
    />,
  );
}

beforeEach(() => {
  localStorage.setItem("commerce-language", "en");
  vi.spyOn(api, "product").mockResolvedValue(product);
  vi.spyOn(api, "products").mockResolvedValue([product]);
  vi.spyOn(api, "productVariants").mockResolvedValue([]);
  vi.spyOn(api, "inventoryHistory").mockResolvedValue([]);
});
afterEach(() => vi.restoreAllMocks());

it("locks aggregate stock when multiple active variants require targeted adjustments", async () => {
  vi.mocked(api.productVariants).mockResolvedValue(
    ["default", "blue"].map((variant_id, id) => ({
      id,
      variant_id,
      title: variant_id,
      sku: variant_id,
      options: {},
      price: "15.00",
      stock: 4,
      stock_policy: "deny" as const,
      status: "active",
      version: 1,
      created_at: product.created_at,
      updated_at: product.updated_at,
    })),
  );
  renderDetail();
  await screen.findByText("blue", { selector: "b" }, { timeout: 3000 });
  expect(
    (screen.getByLabelText("Stock", { exact: true }) as HTMLInputElement)
      .readOnly,
  ).toBe(true);
  expect(
    screen.getByText("Adjust stock per variant in Variants & inventory below."),
  ).toBeTruthy();
});

it("defaults to a localized dense list, preserves search in the detail link, and clears empty filters", async () => {
  render(
    <MemoryRouter>
      <LanguageProvider>
        <ProductsPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole("table", { name: "Products table" }),
  ).toBeTruthy();
  expect(screen.getByText("1,500.25 USD")).toBeTruthy();
  expect(screen.getByText("Active")).toBeTruthy();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "headphones" },
  });
  expect(
    screen.getByRole("link", { name: "Study headphones" }).getAttribute("href"),
  ).toContain("q=headphones&product=P101");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "absent" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByRole("link", { name: "Study headphones" })).toBeTruthy();
});

it("saves a review through the strict API before enabling explicit activation", async () => {
  vi.spyOn(api, "review").mockResolvedValue(reviewed);
  vi.spyOn(api, "activate").mockResolvedValue({
    ...reviewed,
    status: "active",
  });
  renderDetail();
  await screen.findByRole("heading", { name: product.name });
  fireEvent.change(screen.getByRole("textbox", { name: "Name" }), {
    target: { value: reviewed.name },
  });
  expect(
    (
      screen.getByRole("button", {
        name: "Activate product",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save review" }));
  await screen.findByText("Reviewed", { selector: ".badge" });
  expect(api.review).toHaveBeenCalledWith("P101", {
    name: reviewed.name,
    category: "Audio",
    description: product.description,
    features: ["Bluetooth"],
    customer_benefits: ["Portable"],
  });
  expect(api.activate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Activate product" }));
  await screen.findByText("Product activated.");
  expect(api.activate).toHaveBeenCalledWith("P101");
});

it("omits provider-owned price and stock even if a client changes their draft values", () => {
  const input = productReviewInput(
    { ...product, source_of_truth: "external" },
    {
      name: product.name,
      category: product.category,
      description: product.description,
      features: "Bluetooth",
      benefits: "Portable",
      price: "2",
      stock: "100",
    },
  );
  expect(input).not.toHaveProperty("price");
  expect(input).not.toHaveProperty("stock");
});

it("disables provider financial fields and all write actions for a read-only role", async () => {
  vi.mocked(api.product).mockResolvedValue({
    ...product,
    source_of_truth: "external",
    source_provider: "shopify",
  });
  const { unmount } = renderDetail();
  await screen.findByText("shopify");
  expect(
    (
      screen
        .getByRole("spinbutton", { name: "Price (USD)" })
        .closest("fieldset") as HTMLFieldSetElement
    ).disabled,
  ).toBe(true);
  unmount();
  renderDetail({ canEdit: false });
  await screen.findByText(/Your role can view products/);
  expect(screen.queryByRole("button", { name: "Save review" })).toBeNull();
  expect(
    (
      screen
        .getByRole("textbox", { name: "Name" })
        .closest("fieldset") as HTMLFieldSetElement
    ).disabled,
  ).toBe(true);
});

it("keeps rejected edits and allows a successful retry", async () => {
  vi.spyOn(api, "review")
    .mockRejectedValueOnce(
      new ApiError(409, {
        code: "inventory_conflict",
        message: "Use variant stock adjustments",
        details: {},
        request_id: "test",
      }),
    )
    .mockResolvedValue(reviewed);
  renderDetail();
  const name = await screen.findByRole("textbox", {
    name: "Name",
  });
  fireEvent.change(name, { target: { value: reviewed.name } });
  fireEvent.click(screen.getByRole("button", { name: "Save review" }));
  await screen.findByText(/Use variant stock adjustments/);
  expect((name as HTMLInputElement).value).toBe(reviewed.name);
  fireEvent.click(screen.getByRole("button", { name: "Save review" }));
  await screen.findByText("Reviewed", { selector: ".badge" });
  expect(api.review).toHaveBeenCalledTimes(2);
});

it("recovers a failed deep link load without showing stale product data", async () => {
  vi.mocked(api.product).mockRejectedValueOnce(new Error("Unavailable"));
  renderDetail();
  await screen.findByText("The product could not be loaded.");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("heading", { name: product.name });
});

it("prevents duplicate saves while the first request is pending and ignores a response after unmount", async () => {
  let resolve!: (value: ProductRecord) => void;
  vi.spyOn(api, "review").mockReturnValue(
    new Promise((yes) => {
      resolve = yes;
    }),
  );
  const updated = vi.fn();
  const { unmount } = renderDetail({ onUpdated: updated });
  const name = await screen.findByRole("textbox", {
    name: "Name",
  });
  fireEvent.change(name, { target: { value: reviewed.name } });
  const form = name.closest("form")!;
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(api.review).toHaveBeenCalledTimes(1);
  unmount();
  await act(async () => resolve(reviewed));
  expect(updated).not.toHaveBeenCalled();
});

it("requires confirmation before discarding an unsaved review", async () => {
  const back = vi.fn();
  vi.spyOn(window, "confirm").mockReturnValue(false);
  renderDetail({ onBack: back });
  const name = await screen.findByRole("textbox", {
    name: "Name",
  });
  fireEvent.change(name, { target: { value: "Unsaved" } });
  fireEvent.click(screen.getByRole("button", { name: "Back to products" }));
  expect(back).not.toHaveBeenCalled();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Discard changes" }));
  await waitFor(() =>
    expect((name as HTMLInputElement).value).toBe(product.name),
  );
});
