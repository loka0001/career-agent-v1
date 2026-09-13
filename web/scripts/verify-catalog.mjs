import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright-core";

const baseUrl = process.env.UI_BASE_URL ?? "http://127.0.0.1:5173";
if (!process.env.UI_DEMO_PASSWORD)
  throw new Error(
    "UI_DEMO_PASSWORD is required for isolated demo verification",
  );
const evidence = new URL("../../artifacts/ui-catalog/", import.meta.url);
await mkdir(evidence, { recursive: true });
const browser = await chromium.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
let expectedMissing = false;
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error" && !expectedMissing)
    errors.push(message.text());
});
page.on("response", (response) => {
  if (
    response.status() >= 400 &&
    !(
      expectedMissing &&
      response.status() === 404 &&
      response.url().endsWith("/api/v1/products/QA-MISSING-CATALOG")
    )
  )
    errors.push(`${response.status()} ${response.url()}`);
});
page.on("requestfailed", (request) =>
  errors.push(
    `${request.method()} ${request.url()}: ${request.failure()?.errorText}`,
  ),
);

async function persist(button, method, path, expectedStatus = 200) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (res) =>
        res.request().method() === method &&
        new URL(res.url()).pathname === path,
    ),
    button.click(),
  ]);
  assert.equal(response.status(), expectedStatus, await response.text());
  return response.json();
}
async function overflowCheck() {
  const dimensions = await page.evaluate(() => ({
    body: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  assert.ok(
    dimensions.body <= dimensions.viewport,
    `Page overflow: ${JSON.stringify(dimensions)}`,
  );
  assert.equal(await page.locator("vite-error-overlay").count(), 0);
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.evaluate(() =>
    window.localStorage.setItem("commerce-language", "en"),
  );
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Email", { exact: true }).fill("merchant@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.UI_DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/app/command");
  await page.getByRole("heading", { name: "Command Center" }).waitFor();
  errors.length = 0; // Anonymous-session 401 before login is expected.
  const products = await page.evaluate(async () => {
    const response = await globalThis.fetch("/api/v1/products");
    if (!response.ok) throw new Error("Catalog did not load");
    return response.json();
  });
  const candidates = products.filter(
    (item) =>
      item.source_of_truth === "local" &&
      item.status === "active" &&
      item.stock > 5,
  );
  let original;
  for (const candidate of candidates) {
    const variants = await page.evaluate(
      async (id) =>
        (
          await globalThis.fetch(
            `/api/v1/products/${encodeURIComponent(id)}/variants`,
          )
        ).json(),
      candidate.product_id,
    );
    if (
      variants.filter((variant) => variant.status === "active").length === 1
    ) {
      original = candidate;
      break;
    }
  }
  assert.ok(original, "The isolated seed must contain an active local product");
  const path = `/api/v1/products/${encodeURIComponent(original.product_id)}`;
  await page.goto(`${baseUrl}/app/products`, { waitUntil: "networkidle" });
  await page.getByRole("table", { name: "Products table" }).waitFor();
  await page.getByRole("searchbox").fill("QA-NO-MATCH-82391");
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page.getByRole("searchbox").fill(original.product_id);
  await page.getByRole("link", { name: original.name, exact: true }).click();
  assert.equal(new URL(page.url()).searchParams.get("q"), original.product_id);
  await page
    .getByRole("heading", { name: original.name, exact: true })
    .waitFor();
  const detailUrl = page.url();
  const price = page.getByLabel(`Price (${original.currency})`, {
    exact: true,
  });
  await price.fill("0");
  assert.equal(
    await price.evaluate((input) => input.validity.rangeUnderflow),
    true,
  );
  await price.fill((Number(original.price) + 0.01).toFixed(2));
  await page
    .getByLabel("Stock", { exact: true })
    .fill(String(original.stock + 1));
  await page
    .getByLabel("Name", { exact: true })
    .fill(`${original.name} QA reviewed`);
  assert.equal(
    await page.getByRole("button", { name: "Activate product" }).isDisabled(),
    true,
  );
  const saved = await persist(
    page.getByRole("button", { name: "Save review" }),
    "PATCH",
    path,
  );
  assert.equal(saved.status, "reviewed");
  assert.equal(saved.stock, original.stock + 1);
  assert.equal(
    Number(saved.price),
    Number((Number(original.price) + 0.01).toFixed(2)),
  );
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(
    await page.getByLabel("Name", { exact: true }).inputValue(),
    saved.name,
  );
  assert.equal(
    await page.getByLabel("Stock", { exact: true }).inputValue(),
    String(saved.stock),
  );
  const activated = await persist(
    page.getByRole("button", { name: "Activate product" }),
    "POST",
    `${path}/activate`,
  );
  assert.equal(activated.status, "active");
  await page.getByRole("button", { name: "Back to products" }).click();
  assert.equal(
    await page.getByRole("searchbox").inputValue(),
    original.product_id,
  );
  await page.getByRole("link", { name: saved.name, exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill(original.name);
  await price.fill(original.price);
  await page.getByLabel("Stock", { exact: true }).fill(String(original.stock));
  await persist(
    page.getByRole("button", { name: "Save review" }),
    "PATCH",
    path,
  );
  await persist(
    page.getByRole("button", { name: "Activate product" }),
    "POST",
    `${path}/activate`,
  );
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(await price.inputValue(), original.price);
  assert.equal(
    await page.getByLabel("Stock", { exact: true }).inputValue(),
    String(original.stock),
  );

  // Variant operations use a signed adjustment and an auditable opening balance.
  const inventory = page.getByRole("region", { name: "Variants & inventory" });
  await inventory
    .getByRole("button", { name: "Add variant", exact: true })
    .click();
  const variantId = `qa-${Date.now()}`;
  await inventory.getByLabel("Variant ID", { exact: true }).fill(variantId);
  await inventory
    .getByLabel("Variant name", { exact: true })
    .fill("QA Blue variant");
  await inventory.getByLabel("SKU", { exact: true }).fill(variantId);
  await inventory
    .getByLabel(`Price (${original.currency})`, { exact: true })
    .fill("99.50");
  await inventory.getByLabel("Opening stock", { exact: true }).fill("3");
  await inventory.getByRole("button", { name: "Add option" }).click();
  await inventory.getByLabel("Option name 1").fill("Color");
  await inventory.getByLabel("Option value 1").fill("Blue");
  await persist(
    inventory.getByRole("button", { name: "Add variant", exact: true }),
    "POST",
    `${path}/variants`,
    201,
  );
  await page.getByText("Variant added and opening stock recorded.").waitFor();
  await inventory.getByRole("combobox").selectOption(variantId);
  await inventory.getByLabel("Quantity change").fill("-2");
  await inventory.getByLabel("Reason", { exact: true }).fill("QA stocktake");
  const adjustment = await persist(
    inventory.getByRole("button", { name: "Adjust stock", exact: true }),
    "POST",
    `${path}/inventory/adjust`,
  );
  assert.equal(adjustment.variant_id, variantId);
  assert.equal(adjustment.quantity_before, 3);
  assert.equal(adjustment.quantity_after, 1);
  await page.reload({ waitUntil: "networkidle" });
  await inventory.getByText("QA stocktake", { exact: true }).waitFor();
  await inventory.getByRole("combobox").selectOption(variantId);
  await inventory.getByLabel("Quantity change").fill("-1");
  await inventory
    .getByLabel("Reason", { exact: true })
    .fill("QA restore aggregate stock");
  await persist(
    inventory.getByRole("button", { name: "Adjust stock", exact: true }),
    "POST",
    `${path}/inventory/adjust`,
  );
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(
    await page.getByLabel("Stock", { exact: true }).inputValue(),
    String(original.stock),
  );

  const screenshots = [];
  for (const language of ["en", "ar"]) {
    for (const width of [1440, 768, 390]) {
      const theme = width === 1440 ? "dark" : "light";
      await page.evaluate(
        ({ language, theme }) => {
          window.localStorage.setItem("commerce-language", language);
          window.localStorage.setItem("commerce-theme", theme);
        },
        { language, theme },
      );
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(detailUrl, { waitUntil: "networkidle" });
      await page
        .getByRole("heading", { name: original.name, exact: true })
        .waitFor();
      assert.equal(
        await page.locator("html").getAttribute("dir"),
        language === "ar" ? "rtl" : "ltr",
      );
      await overflowCheck();
      const detail = `catalog-detail-${language}-${width}-${theme}.png`;
      await page.screenshot({
        path: new URL(detail, evidence).pathname.replace(/^\/(\w:)/, "$1"),
        fullPage: true,
      });
      await page.goto(`${baseUrl}/app/products`, { waitUntil: "networkidle" });
      await page.getByRole("table").waitFor();
      await overflowCheck();
      if (width === 390) {
        const cells = page
          .locator(".product-table-row:not(.product-table-head)")
          .first()
          .locator('[role="cell"]');
        for (const cell of await cells.all()) {
          const bounds = await cell.boundingBox();
          assert.ok(
            bounds && bounds.x >= 0 && bounds.x + bounds.width <= width,
            "A mobile product field is clipped offscreen",
          );
        }
      }
      const list = `catalog-list-${language}-${width}-${theme}.png`;
      await page.screenshot({
        path: new URL(list, evidence).pathname.replace(/^\/(\w:)/, "$1"),
        fullPage: true,
      });
      screenshots.push(detail, list);
    }
  }
  await page.evaluate(() =>
    window.localStorage.setItem("commerce-language", "en"),
  );
  expectedMissing = true;
  await page.goto(`${baseUrl}/app/products?product=QA-MISSING-CATALOG`, {
    waitUntil: "networkidle",
  });
  await page.getByText("The product could not be loaded.").waitFor();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await page.getByText("The product could not be loaded.").waitFor();
  await page.getByRole("button", { name: "Back to products" }).click();
  await page.getByRole("table").waitFor();
  expectedMissing = false;
  await page.goto(`${baseUrl}/app/products/new`, { waitUntil: "networkidle" });
  const newProductId = `QA-${Date.now()}`;
  await page.getByLabel("Product ID", { exact: false }).fill(newProductId);
  await page.getByLabel("Name", { exact: true }).fill("QA Study Headphones");
  await page.getByLabel("Price (EGP)", { exact: true }).fill("499.00");
  await page.getByLabel("Stock", { exact: true }).fill("6");
  await page
    .getByLabel("Specifications — one per line")
    .fill("Bluetooth 5.3\nMicrophone");
  await page
    .getByLabel("JPEG, PNG, or WebP image (maximum 10 MB)")
    .setInputFiles({
      name: "qa.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDLsAAAAASUVORK5CYII=",
        "base64",
      ),
    });
  await page.getByRole("button", { name: "Analyze product" }).click();
  await page
    .getByRole("heading", { name: "2. Review extracted facts" })
    .waitFor();
  await page.getByRole("button", { name: "Save and activate" }).click();
  await page.getByRole("button", { name: "Create content" }).click();
  const facebook = page.getByLabel("Facebook text");
  await facebook.fill(`${await facebook.inputValue()} Merchant reviewed.`);
  assert.equal(
    await page.getByRole("button", { name: "Explicit approval" }).isDisabled(),
    true,
  );
  await page.getByRole("button", { name: "Save changes" }).click();
  await page
    .getByText("Changes saved. Any previous approval has been cleared.")
    .waitFor();
  await page.getByRole("button", { name: "Explicit approval" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Publish to both platforms" }).click();
  await page
    .getByText("Demo completed — no live post was created", { exact: true })
    .first()
    .waitFor();
  assert.equal(
    await page
      .getByText("Demo completed — no live post was created", { exact: true })
      .count(),
    2,
  );
  await overflowCheck();
  assert.deepEqual(errors, [], "Unexpected browser/network errors");
  console.log(
    JSON.stringify({
      catalog: {
        search_clear_detail: true,
        native_price_validation: true,
        review_reloaded: true,
        activation_separate: true,
        price_stock_restored: true,
        missing_detail_retry: true,
        variant_creation_opening_ledger: true,
        variant_adjust_reload: true,
        onboard_review_edit_approve_demo_publish: true,
      },
      screenshots,
      unexpected_errors: 0,
    }),
  );
} finally {
  await browser.close();
}
