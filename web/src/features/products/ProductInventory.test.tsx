import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { api, ApiError } from "../../lib/api";
import type {
  InventoryTransaction,
  ProductRecord,
  ProductVariant,
} from "../../lib/types";
import { ProductInventory } from "./ProductInventory";

const product = {
  product_id: "P1",
  store_id: "S1",
  currency: "USD",
  stock: 5,
  source_of_truth: "local",
} as ProductRecord;
const variant: ProductVariant = {
  id: 1,
  variant_id: "default",
  title: "Blue shirt",
  sku: "BLUE",
  options: { Color: "Blue" },
  price: "15.25",
  stock: 5,
  stock_policy: "deny",
  status: "active",
  version: 1,
  created_at: "2026-09-08T03:00:00Z",
  updated_at: "2026-09-08T03:00:00Z",
};
const transaction: InventoryTransaction = {
  id: 10,
  product_id: "P1",
  variant_id: "default",
  delta: 2,
  quantity_before: 5,
  quantity_after: 7,
  reason: "Received",
  reference_type: "manual",
  reference_id: "",
  actor_user_id: "merchant",
  created_at: "2026-09-08T03:00:00Z",
  idempotency_key: "unused",
};
function show(props: Partial<Parameters<typeof ProductInventory>[0]> = {}) {
  return render(
    <ProductInventory
      product={product}
      language="en"
      canEdit
      disabled={false}
      onBusy={vi.fn()}
      onUpdated={vi.fn()}
      {...props}
    />,
  );
}
beforeEach(() => {
  sessionStorage.clear();
  vi.spyOn(api, "productVariants").mockResolvedValue([variant]);
  vi.spyOn(api, "inventoryHistory").mockResolvedValue([]);
  vi.spyOn(api, "product").mockResolvedValue({ ...product, stock: 7 });
});
afterEach(() => vi.restoreAllMocks());

it("shows authoritative variants and submits a signed delta with audit reason", async () => {
  const updated = vi.fn();
  vi.spyOn(api, "adjustInventory").mockResolvedValue(transaction);
  show({ onUpdated: updated });
  await screen.findByText("15.25 USD");
  fireEvent.change(screen.getByLabelText("Quantity change"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Received" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Adjust stock" }));
  await screen.findByText("Stock adjustment recorded.");
  expect(api.adjustInventory).toHaveBeenCalledWith(
    "P1",
    expect.objectContaining({
      variant_id: "default",
      delta: 2,
      reason: "Received",
      allow_negative: false,
      idempotency_key: expect.stringMatching(/^inventory-/),
    }),
  );
  await waitFor(() =>
    expect(updated).toHaveBeenCalledWith(expect.objectContaining({ stock: 7 })),
  );
  expect(sessionStorage.length).toBe(0);
});

it("recovers an ambiguous adjustment after remount using the identical payload and key", async () => {
  vi.spyOn(api, "adjustInventory")
    .mockRejectedValueOnce(new Error("Lost response"))
    .mockResolvedValue(transaction);
  const first = show();
  await screen.findByText("Blue shirt", { selector: "b" });
  fireEvent.change(screen.getByLabelText("Quantity change"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Received" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Adjust stock" }));
  await screen.findByRole("button", { name: "Retry same adjustment" });
  const payload = vi.mocked(api.adjustInventory).mock.calls[0]![1];
  first.unmount();
  show();
  const retry = await screen.findByRole("button", {
    name: "Retry same adjustment",
  });
  expect(
    (
      screen
        .getByLabelText("Quantity change")
        .closest("fieldset") as HTMLFieldSetElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(retry);
  await screen.findByText("Stock adjustment recorded.");
  expect(vi.mocked(api.adjustInventory).mock.calls[1]![1]).toEqual(payload);
  expect(sessionStorage.length).toBe(0);
});

it("keeps a rejected correction editable and does not retry a completed mutation after refresh failure", async () => {
  vi.spyOn(api, "adjustInventory")
    .mockRejectedValueOnce(
      new ApiError(409, {
        code: "CONFLICT",
        message: "Rejected",
        details: {},
        request_id: "test",
      }),
    )
    .mockResolvedValue(transaction);
  show();
  await screen.findByText("Blue shirt", { selector: "b" });
  fireEvent.change(screen.getByLabelText("Quantity change"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Received" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Adjust stock" }));
  await screen.findByText(/Your inputs are preserved/);
  expect(
    (screen.getByLabelText("Quantity change") as HTMLInputElement).value,
  ).toBe("2");
  vi.mocked(api.product).mockRejectedValueOnce(new Error("Refresh failed"));
  fireEvent.click(screen.getByRole("button", { name: "Adjust stock" }));
  await waitFor(() =>
    expect(
      screen.getAllByText(/Inventory could not be loaded/).length,
    ).toBeGreaterThan(0),
  );
  expect(
    screen.queryByRole("button", { name: "Retry same adjustment" }),
  ).toBeNull();
  expect(sessionStorage.length).toBe(0);
});

it("shows read-only provider inventory and ledger while preserving negative quantities", async () => {
  vi.mocked(api.productVariants).mockResolvedValue([
    { ...variant, stock: -1, stock_policy: "continue" },
  ]);
  vi.mocked(api.inventoryHistory).mockResolvedValue([transaction]);
  show({ product: { ...product, source_of_truth: "external" } });
  await screen.findByText("Backorders allowed");
  expect(screen.getByText("-1")).toBeTruthy();
  expect(screen.getByText("Received")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Adjust stock" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Add variant" })).toBeNull();
});

it("creates a variant with options and opening stock using the real input contract", async () => {
  vi.spyOn(api, "createProductVariant").mockResolvedValue({
    ...variant,
    variant_id: "red",
    sku: "RED",
    title: "Red shirt",
    stock: 3,
  });
  show();
  await screen.findByText("Blue shirt", { selector: "b" });
  fireEvent.click(screen.getByRole("button", { name: "Add variant" }));
  for (const [label, value] of [
    ["Variant ID", "red"],
    ["Variant name", "Red shirt"],
    ["SKU", "RED"],
    ["Price (USD)", "17.50"],
    ["Opening stock", "3"],
  ] as const)
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Add option" }));
  fireEvent.change(screen.getByLabelText("Option name 1"), {
    target: { value: "Color" },
  });
  fireEvent.change(screen.getByLabelText("Option value 1"), {
    target: { value: "Red" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add variant" }));
  await screen.findByText("Variant added and opening stock recorded.");
  expect(api.createProductVariant).toHaveBeenCalledWith("P1", {
    variant_id: "red",
    title: "Red shirt",
    sku: "RED",
    price: "17.50",
    stock: 3,
    stock_policy: "deny",
    options: { Color: "Red" },
  });
});

it("blocks edits after a load failure and offers a genuine refresh", async () => {
  vi.mocked(api.inventoryHistory).mockRejectedValueOnce(new Error("Offline"));
  show({ language: "ar" });
  await screen.findByText(
    "تعذر تحميل المخزون. أعد المحاولة قبل إجراء تغييرات.",
  );
  expect(
    (screen.getByRole("button", { name: "إضافة متغير" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "تحديث المخزون" }));
  await screen.findByText("Blue shirt", { selector: "b" });
  expect(
    (screen.getByRole("button", { name: "إضافة متغير" }) as HTMLButtonElement)
      .disabled,
  ).toBe(false);
});
