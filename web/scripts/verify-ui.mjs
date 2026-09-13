import assert from "node:assert/strict";
import { mkdir, stat } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright-core";

const baseUrl = process.env.UI_BASE_URL ?? "http://127.0.0.1:5173";
const demoPassword = process.env.UI_DEMO_PASSWORD;
if (!demoPassword) {
  throw new Error(
    "UI_DEMO_PASSWORD is required; use the one-time password printed by scripts.bootstrap_env",
  );
}
const outputDirectory = new URL(
  "../../artifacts/ui-verification/",
  import.meta.url,
);
await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  colorScheme: "light",
});
const page = await context.newPage();
const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];
const errorResponses = [];

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("requestfailed", (request) => {
  failedRequests.push(
    `${request.method()} ${request.url()}: ${request.failure()?.errorText}`,
  );
});
page.on("response", (response) => {
  if (response.status() >= 400) {
    errorResponses.push({
      status: response.status(),
      url: response.url(),
      page: page.url(),
    });
  }
});

async function screenshot(name) {
  const path = new URL(`${name}.png`, outputDirectory);
  await page.screenshot({ path: path.pathname.slice(1), fullPage: true });
  const info = await stat(path);
  return { name, bytes: info.size };
}

async function dimensions() {
  return page.evaluate(() => ({
    bodyWidth: document.body.scrollWidth,
    viewportWidth: window.innerWidth,
    heading:
      document.querySelector(".page-heading h1")?.textContent?.trim() ?? "",
    direction: document.documentElement.dir,
    accessibilityIssues: [
      ...[...document.querySelectorAll("input, select, textarea")]
        .filter((element) => {
          const control = /** @type {HTMLInputElement} */ (element);
          if (
            control.type === "hidden" ||
            getComputedStyle(control).display === "none"
          ) {
            return false;
          }
          return !(
            control.labels?.length ||
            control.getAttribute("aria-label") ||
            control.getAttribute("aria-labelledby")
          );
        })
        .map(
          (element) => `unlabelled-control:${element.tagName.toLowerCase()}`,
        ),
      ...[...document.querySelectorAll("button, a[href]")]
        .filter((element) => {
          if (getComputedStyle(element).display === "none") return false;
          return !(
            element.textContent?.trim() ||
            element.getAttribute("aria-label") ||
            element.getAttribute("aria-labelledby") ||
            element.getAttribute("title")
          );
        })
        .map((element) => `unnamed-action:${element.tagName.toLowerCase()}`),
      ...[...document.querySelectorAll("img:not([alt])")].map(
        () => "image-missing-alt",
      ),
    ],
  }));
}

const screenshots = [];
const publicChecks = [];
const stateChecks = {};

// Public entry: truthful content, persisted locale, and all target viewport widths.
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
await page
  .getByRole("heading", {
    name: "شغّل تجارتك بوضوح، واستعد فرص الإيراد قبل أن تضيع.",
  })
  .waitFor();
let publicDimensions = await dimensions();
assert.equal(publicDimensions.bodyWidth, 1440);
publicChecks.push({ viewport: 1440, ...publicDimensions });
screenshots.push(await screenshot("landing-dark-desktop"));
await page.setViewportSize({ width: 768, height: 1024 });
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
await page
  .getByRole("heading", {
    name: "شغّل تجارتك بوضوح، واستعد فرص الإيراد قبل أن تضيع.",
  })
  .waitFor();
publicDimensions = await dimensions();
publicChecks.push({ viewport: 768, ...publicDimensions });
screenshots.push(await screenshot("landing-dark-tablet"));
await page.setViewportSize({ width: 390, height: 844 });
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
await page
  .getByRole("heading", {
    name: "شغّل تجارتك بوضوح، واستعد فرص الإيراد قبل أن تضيع.",
  })
  .waitFor();
publicDimensions = await dimensions();
publicChecks.push({ viewport: 390, ...publicDimensions });
screenshots.push(await screenshot("landing-dark-mobile"));
await page.setViewportSize({ width: 1440, height: 900 });
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "التبديل إلى الإنجليزية" }).click();
await page.waitForFunction(() => document.documentElement.dir === "ltr");
await page
  .getByRole("heading", {
    name: "Operate commerce clearly, and recover revenue before it slips away.",
  })
  .waitFor();
screenshots.push(await screenshot("landing-dark-english-desktop"));
await page.getByRole("button", { name: "Switch to Arabic" }).click();
await page.waitForFunction(() => document.documentElement.dir === "rtl");

// Real authenticated session.
await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
await page.getByLabel("البريد الإلكتروني").fill("merchant@example.com");
await page.locator('input[type="password"]').fill(demoPassword);
await page.getByRole("button", { name: "دخول إلى اللوحة" }).click();
await page.waitForURL("**/app/command");
await page.getByRole("heading", { name: "مركز القيادة" }).waitFor();
await page.getByText("وصول مجاني · بلا بطاقة").first().waitFor();
await page.getByText("بيئة تجريبية · بيانات معزولة").first().waitFor();

// Initial anonymous /me calls are expected; authenticated acceptance starts here.
consoleErrors.length = 0;
errorResponses.length = 0;

const routes = [
  "command",
  "inbox",
  "products",
  "products/new",
  "orders",
  "opportunities",
  "automations",
  "studio",
  "calendar",
  "analytics",
  "customers",
  "integrations",
  "agent-settings",
  "team",
  "api-keys",
  "settings",
  "security",
  "onboarding",
  "privacy",
  "billing",
];
const routeChecks = [];

for (const route of routes) {
  await page.goto(`${baseUrl}/app/${route}`, { waitUntil: "networkidle" });
  await page.locator(".page-heading h1").waitFor();
  const result = await dimensions();
  routeChecks.push({
    route,
    ...result,
    overflow: result.bodyWidth > result.viewportWidth + 1,
  });
}

// Free access is explicit and cannot expose a checkout or an upgrade grid.
await page.goto(`${baseUrl}/app/billing`, { waitUntil: "networkidle" });
await page
  .getByRole("heading", {
    name: "وصول مجاني كامل — بلا بطاقة بنكية",
  })
  .waitFor();
assert.equal(await page.locator(".plan-card").count(), 0);
assert.equal(await page.getByText("اختيار المستوى").count(), 0);
screenshots.push(await screenshot("access-light-desktop"));

// Create a real draft order through the UI, prepare COD, then cancel to release stock.
await page.goto(`${baseUrl}/app/orders`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "طلب جديد" }).click();
const orderForm = page.locator(".order-create-panel form");
await orderForm.waitFor();
await orderForm.getByRole("button", { name: "إنشاء وحجز المخزون" }).click();
await page.getByText(/أُنشئ الطلب #\d+ وحُجز المخزون مرة واحدة/).waitFor();
await page.getByRole("button", { name: "نقل إلى بانتظار التأكيد" }).click();
await page.getByRole("button", { name: "تجهيز التحصيل" }).click();
await page
  .getByText("تم تجهيز الطلب للدفع عند الاستلام، دون رابط أو بطاقة.")
  .waitFor();
page.once("dialog", (dialog) => dialog.accept());
await page.getByRole("button", { name: "إلغاء الطلب" }).click();
await page.getByText("انتقل الطلب إلى «ملغي».").waitFor();
screenshots.push(await screenshot("orders-cod-light-desktop"));

// English content and LTR are verified across every primary route.
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "تغيير اللغة" }).click();
await page.waitForFunction(() => document.documentElement.dir === "ltr");
const englishHeadings = {
  command: "Command Center",
  inbox: "Inbox",
  products: "Products",
  "products/new": "Add and publish a product",
  orders: "Orders",
  opportunities: "Revenue Opportunities",
  automations: "Automations",
  studio: "Content studio",
  calendar: "Campaign calendar",
  analytics: "Analytics",
  customers: "Customers",
  integrations: "Integrations",
  "agent-settings": "Sales assistant settings",
  team: "Team & permissions",
  "api-keys": "API keys & website",
  settings: "Store settings",
  security: "Account security",
  onboarding: "Store readiness",
  privacy: "Privacy & retention",
  billing: "Access & usage",
};
for (const [route, heading] of Object.entries(englishHeadings)) {
  await page.goto(`${baseUrl}/app/${route}`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: heading, exact: true }).waitFor();
  assert.equal(await page.evaluate(() => document.documentElement.dir), "ltr");
}
await page.goto(`${baseUrl}/app/inbox`, { waitUntil: "networkidle" });
await page.locator(".conversation-row").first().click();
const englishContext = page.getByLabel("Customer & commerce context");
await englishContext.locator(".inbox-context__metrics").waitFor();
assert.equal(
  await englishContext.getByRole("link", { name: "View all orders" }).count(),
  1,
);
const englishInboxDimensions = await dimensions();
assert.ok(
  englishInboxDimensions.bodyWidth <= englishInboxDimensions.viewportWidth,
  "English desktop Inbox overflows horizontally",
);
screenshots.push(await screenshot("inbox-context-light-english-desktop"));
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await Promise.all([
  page.getByRole("heading", { name: "Needs attention" }).waitFor(),
  page.getByText("Conversations awaiting reply", { exact: true }).waitFor(),
  page.getByText("Content awaiting review", { exact: true }).waitFor(),
  page.getByText("Publishing needs attention", { exact: true }).waitFor(),
  page.getByText("Channels requiring setup", { exact: true }).waitFor(),
  page.getByRole("heading", { name: "Recent outcomes" }).waitFor(),
]);
assert.equal(
  await page.getByRole("button", { name: "Open notifications" }).count(),
  0,
);
assert.deepEqual(
  await page.locator(".sidebar .nav-group--primary a").allTextContents(),
  [
    "Command Center",
    "Inbox",
    "Content Studio",
    "Products",
    "Integrations",
    "Store Settings",
  ],
);
const moreTools = page.locator(".sidebar .nav-more");
assert.equal(await moreTools.getAttribute("open"), null);
await moreTools.locator("summary").click();
await moreTools.getByRole("link", { name: "Opportunities" }).waitFor();
assert.equal(await moreTools.getByRole("link", { name: "Billing" }).count(), 0);
await moreTools.locator("summary").click();
screenshots.push(await screenshot("access-light-english-desktop"));

// Return to Arabic for the visual theme/device matrix.
await page.getByRole("button", { name: "Switch language" }).click();
await page.waitForFunction(() => document.documentElement.dir === "rtl");
await page.goto(`${baseUrl}/app/inbox`, { waitUntil: "networkidle" });
await page.locator(".conversation-row").first().click();
const arabicContext = page.getByLabel("سياق العميل والمتجر");
await arabicContext.locator(".inbox-context__metrics").waitFor();
screenshots.push(await screenshot("inbox-context-light-arabic-desktop"));
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "مركز القيادة" }).waitFor();
const themeControl = page.locator(".topbar-actions").getByRole("button", {
  name: /theme|mode/i,
});
if ((await themeControl.getAttribute("title")) === "System theme") {
  await themeControl.click();
}
if ((await themeControl.getAttribute("title")) === "Dark mode") {
  await themeControl.click();
}
await page.waitForFunction(
  () => document.documentElement.dataset.theme === "dark",
);
screenshots.push(await screenshot("command-dark-desktop"));
await themeControl.click();
await page.waitForFunction(
  () => document.documentElement.dataset.theme === "light",
);
screenshots.push(await screenshot("command-light-desktop"));

await page.setViewportSize({ width: 768, height: 1024 });
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "مركز القيادة" }).waitFor();
const tabletDimensions = await dimensions();
screenshots.push(await screenshot("command-light-tablet"));

await page.setViewportSize({ width: 390, height: 844 });
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "مركز القيادة" }).waitFor();
screenshots.push(await screenshot("command-light-mobile"));
assert.deepEqual(
  await page.locator(".mobile-nav a").evaluateAll((links) =>
    links.map((link) => ({
      href: link.getAttribute("href"),
      label: link.textContent?.trim(),
    })),
  ),
  [
    { href: "/app/command", label: "مركز القيادة" },
    { href: "/app/inbox", label: "الرسائل" },
    { href: "/app/studio", label: "استوديو المحتوى" },
    { href: "/app/products", label: "المنتجات" },
  ],
);
const menuTrigger = page.locator(".mobile-menu-trigger");
await menuTrigger.click();
const drawer = page.getByRole("dialog", { name: "قائمة التطبيق" });
await drawer.waitFor();
assert.equal(
  await drawer.evaluate((element) => element.contains(document.activeElement)),
  true,
);
await page.keyboard.press("Escape");
await drawer.waitFor({ state: "hidden" });
await page.goto(`${baseUrl}/app/studio`, { waitUntil: "networkidle" });
await page.locator(".mobile-nav").waitFor();
screenshots.push(await screenshot("studio-light-mobile"));
await page.goto(`${baseUrl}/app/inbox`, { waitUntil: "networkidle" });
await page.locator(".conversation-row").first().click();
await page
  .getByLabel("سياق العميل والمتجر")
  .locator(".inbox-context__metrics")
  .waitFor();
const mobileInboxDimensions = await dimensions();
assert.ok(
  mobileInboxDimensions.bodyWidth <= mobileInboxDimensions.viewportWidth,
  "Arabic mobile Inbox overflows horizontally",
);
screenshots.push(await screenshot("inbox-context-light-arabic-mobile"));
const mobileDimensions = await page.evaluate(() => ({
  bodyWidth: document.body.scrollWidth,
  viewportWidth: window.innerWidth,
  mobileNavVisible: (() => {
    const mobileNav = document.querySelector(".mobile-nav");
    return mobileNav ? getComputedStyle(mobileNav).display !== "none" : false;
  })(),
  overflowingElements: [...document.querySelectorAll("*")]
    .filter((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        style.display !== "none" &&
        rect.width > 0 &&
        (rect.right > window.innerWidth + 1 || rect.left < -1)
      );
    })
    .slice(0, 20)
    .map((element) => ({
      tag: element.tagName,
      className: element.className,
      width: element.getBoundingClientRect().width,
      left: element.getBoundingClientRect().left,
      right: element.getBoundingClientRect().right,
    })),
}));

// Required non-happy-path states use safe browser interception, not production mutations.
await page.evaluate(() =>
  window.localStorage.setItem("commerce-language", "en"),
);
await page.route("**/api/v1/billing/subscription", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      plan: {
        key: "starter",
        name: "Restricted acceptance plan",
        price: "0",
        quotas: {},
        features: [],
      },
      status: "active",
      provider: "acceptance-fixture",
      current_period_start: "2026-09-05T00:00:00Z",
      current_period_end: "2026-10-05T00:00:00Z",
      cancel_at_period_end: false,
      trial_end: null,
      usage: {},
    }),
  }),
);
await page.goto(`${baseUrl}/app/products`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Access denied" }).waitFor();
await page
  .getByText("Your current plan does not include this feature.")
  .waitFor();
assert.equal(
  await page.getByRole("link", { name: "Return to Home" }).getAttribute("href"),
  "/app/command",
);
stateChecks.permissionDenied = {
  route: "products",
  direction: await page.evaluate(() => document.documentElement.dir),
};
screenshots.push(await screenshot("products-permission-denied"));
await page.unroute("**/api/v1/billing/subscription");

// Loading and empty states are observed in one delayed, isolated response.
await page.route("**/api/v1/products", async (route) => {
  await delay(700);
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: "[]",
  });
});
await page.goto(`${baseUrl}/app/products`, { waitUntil: "domcontentloaded" });
await page.locator(".product-grid .skeleton").first().waitFor();
stateChecks.loading = { route: "products", visible: true };
await page.getByRole("heading", { name: "No results" }).waitFor();
stateChecks.empty = { route: "products", visible: true };
screenshots.push(await screenshot("products-empty"));
await page.unroute("**/api/v1/products");

// A transport failure must become a useful localized alert, not a blank shell.
const networkFailureOffset = failedRequests.length;
const networkConsoleOffset = consoleErrors.length;
await page.route("**/api/v1/products", (route) =>
  route.abort("internetdisconnected"),
);
await page.goto(`${baseUrl}/app/products`, { waitUntil: "networkidle" });
await page
  .getByRole("alert")
  .getByText("Products could not be loaded")
  .waitFor();
const expectedNetworkFailures = failedRequests.splice(networkFailureOffset);
const expectedNetworkConsoleErrors = consoleErrors.splice(networkConsoleOffset);
assert.ok(
  expectedNetworkFailures.length >= 1 &&
    expectedNetworkFailures.every(
      (message) =>
        message.includes("/api/v1/products") &&
        message.includes("ERR_INTERNET_DISCONNECTED"),
    ),
  `Unexpected network failure evidence: ${JSON.stringify(expectedNetworkFailures)}`,
);
assert.ok(
  expectedNetworkConsoleErrors.every((message) =>
    message.includes("ERR_INTERNET_DISCONNECTED"),
  ),
  `Unexpected network console errors: ${JSON.stringify(expectedNetworkConsoleErrors)}`,
);
stateChecks.networkUnavailable = {
  route: "products",
  requestFailureCount: expectedNetworkFailures.length,
  alert: "Products could not be loaded",
};
screenshots.push(await screenshot("products-network-unavailable"));
await page.unroute("**/api/v1/products");

// Aggregate provider status must identify a disconnected channel in English.
await page.setViewportSize({ width: 1440, height: 1000 });
await page.route("**/api/v1/integrations", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      integrations: [
        {
          name: "facebook",
          configured: false,
          mode: "disconnected",
          masked_identifier: null,
          last_check: null,
        },
      ],
    }),
  }),
);
await page.goto(`${baseUrl}/app/integrations`, { waitUntil: "networkidle" });
await Promise.all([
  page.getByText("Disconnected", { exact: true }).waitFor(),
  page.getByText("Connected accounts", { exact: true }).waitFor(),
]);
stateChecks.providerDisconnected = {
  route: "integrations",
  visible: true,
  englishSectionsVisible: true,
};
screenshots.push(await screenshot("integrations-provider-disconnected"));
await page.getByRole("button", { name: "Store", exact: true }).click();
await page.waitForURL(/section=store/);
await page.getByText("Store and website", { exact: true }).waitFor();
screenshots.push(await screenshot("integrations-store-setup"));
await page.getByRole("button", { name: "WhatsApp", exact: true }).click();
await page.waitForURL(/section=whatsapp/);
await Promise.all([
  page.getByText("Official quick connection", { exact: true }).waitFor(),
  page.getByText("Follow-up templates", { exact: true }).waitFor(),
]);
screenshots.push(await screenshot("integrations-whatsapp-setup"));
await page.unroute("**/api/v1/integrations");

// Team permissions must mirror the authenticated role before any mutation is offered.
await page.goto(`${baseUrl}/app/team`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Team & permissions" }).waitFor();
await page.getByText("You", { exact: true }).waitFor();
const ownerRoleSelect = page.getByLabel("Role for merchant@example.com");
await ownerRoleSelect.waitFor();
assert.equal(await ownerRoleSelect.locator('option[value="owner"]').count(), 1);
assert.equal(
  await page.getByRole("button", { name: "Revoke access" }).count(),
  0,
);
screenshots.push(await screenshot("team-owner-desktop"));

await page.route("**/api/v1/auth/me", async (route) => {
  const response = await route.fetch();
  const body = await response.json();
  body.user.role = "analyst";
  await route.fulfill({ response, json: body });
});
await page.reload({ waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Read-only access" }).waitFor();
assert.equal(await page.getByLabel("Role for merchant@example.com").count(), 0);
assert.equal(
  await page.getByRole("button", { name: "Create invitation" }).count(),
  0,
);
stateChecks.teamPermissions = {
  route: "team",
  ownerCanAssignOwner: true,
  selfRevokeHidden: true,
  analystReadOnly: true,
  backendMutation: false,
};
screenshots.push(await screenshot("team-read-only-desktop"));
await page.unroute("**/api/v1/auth/me");
await page.reload({ waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Invite a member" }).waitFor();

// Assistant settings must preserve the saved persona until the merchant saves.
await page.goto(`${baseUrl}/app/agent-settings`, { waitUntil: "networkidle" });
const assistantNameInput = page.getByLabel("Assistant name");
const originalAssistantName = await assistantNameInput.inputValue();
await assistantNameInput.fill(`${originalAssistantName} QA`);
await page.getByText("Unsaved changes", { exact: true }).waitFor();
assert.equal(
  await page
    .getByRole("button", { name: "Save assistant persona" })
    .isEnabled(),
  true,
);
await page.getByRole("button", { name: "Discard changes" }).click();
await page.getByText("All changes saved", { exact: true }).waitFor();
assert.equal(await assistantNameInput.inputValue(), originalAssistantName);
assert.equal(
  await page
    .getByRole("button", { name: "Save assistant persona" })
    .isDisabled(),
  true,
);
stateChecks.agentSettingsEditState = {
  route: "agent-settings",
  dirtyStateVisible: true,
  discardRestoredOriginal: true,
  backendMutation: false,
};
screenshots.push(await screenshot("agent-settings-desktop"));

// Store settings must expose truthful edit state without persisting a fixture change.
await page.goto(`${baseUrl}/app/settings`, { waitUntil: "networkidle" });
const storeNameInput = page.getByLabel("Store name");
const originalStoreName = await storeNameInput.inputValue();
await storeNameInput.fill(`${originalStoreName} QA`);
await page.getByText("Unsaved changes", { exact: true }).waitFor();
assert.equal(
  await page.getByRole("button", { name: "Save settings" }).isEnabled(),
  true,
);
await page.getByRole("button", { name: "Discard changes" }).click();
await page.getByText("All changes saved", { exact: true }).waitFor();
assert.equal(await storeNameInput.inputValue(), originalStoreName);
assert.equal(
  await page.getByRole("button", { name: "Save settings" }).isDisabled(),
  true,
);
stateChecks.storeSettingsEditState = {
  route: "settings",
  dirtyStateVisible: true,
  discardRestoredOriginal: true,
  backendMutation: false,
};
screenshots.push(await screenshot("settings-desktop"));

// An unavailable AI provider must preserve the conversation and show the API error.
await page.goto(`${baseUrl}/app/inbox`, { waitUntil: "networkidle" });
await page.locator(".conversation-row").first().click();
await page.getByRole("button", { name: "Smart suggestion" }).waitFor();
const aiErrorOffset = errorResponses.length;
const aiConsoleOffset = consoleErrors.length;
await page.route("**/api/v1/inbox/conversations/*/suggest", (route) =>
  route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code: "provider_unavailable",
        message: "AI provider is temporarily unavailable",
        details: {},
        request_id: "ui-ai-unavailable",
      },
    }),
  }),
);
await page.getByRole("button", { name: "Smart suggestion" }).click();
await page
  .getByRole("alert")
  .getByText("AI provider is temporarily unavailable (provider_unavailable)")
  .waitFor();
const expectedAiErrors = errorResponses.splice(aiErrorOffset);
const expectedAiConsoleErrors = consoleErrors.splice(aiConsoleOffset);
assert.ok(
  expectedAiErrors.length === 1 &&
    expectedAiErrors[0].status === 503 &&
    expectedAiErrors[0].url.includes("/api/v1/inbox/conversations/") &&
    expectedAiErrors[0].url.endsWith("/suggest"),
  `Unexpected AI-unavailable responses: ${JSON.stringify(expectedAiErrors)}`,
);
assert.ok(
  expectedAiConsoleErrors.every((message) =>
    message.includes("503 (Service Unavailable)"),
  ),
  `Unexpected AI-unavailable console errors: ${JSON.stringify(expectedAiConsoleErrors)}`,
);
stateChecks.aiUnavailable = {
  route: "inbox",
  responseCount: expectedAiErrors.length,
  conversationPreserved: page.url().endsWith("/app/inbox"),
};
screenshots.push(await screenshot("inbox-ai-unavailable"));
await page.unroute("**/api/v1/inbox/conversations/*/suggest");

// Failed publication is rendered with an actionable, localized explanation.
const failedContentFixture = {
  id: 900001,
  campaign_id: null,
  product_id: "ui-state-fixture",
  content_format: "sales_post",
  platform: "instagram",
  tone: "friendly",
  title: "Publication state acceptance fixture",
  body: "Browser-only fixture; no content is published.",
  caption: "Browser-only fixture",
  hashtags: [],
  cta: "",
  validation_warnings: [],
  status: "failed",
  current_version: 1,
  scheduled_for: null,
  published_at: null,
  external_id: null,
  approved_at: null,
  approved_by: null,
  approved_by_user_id: null,
  created_at: "2026-09-06T00:00:00Z",
  updated_at: "2026-09-06T00:00:00Z",
};
await page.route("**/api/v1/studio/content", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([failedContentFixture]),
  }),
);
await page.goto(`${baseUrl}/app/studio`, { waitUntil: "networkidle" });
await page
  .locator('[data-content-status="failed"]')
  .getByText("Publish failed", { exact: true })
  .waitFor();
await page.getByRole("list", { name: "Review queue" }).waitFor();
assert.equal(await page.locator("article.content-card").count(), 0);
for (const language of ["ar", "en"]) {
  await page.evaluate(
    (value) => window.localStorage.setItem("commerce-language", value),
    language,
  );
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.reload({ waitUntil: "networkidle" });
    await page.locator(".studio-review-queue a").waitFor();
    assert.equal(
      await page.locator("html").getAttribute("dir"),
      language === "ar" ? "rtl" : "ltr",
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      ),
      false,
    );
    screenshots.push(await screenshot(`studio-queue-${language}-${width}`));
  }
}
await page.setViewportSize({ width: 1440, height: 900 });
await page.getByRole("button", { name: "Post editors", exact: true }).click();
await page
  .getByRole("alert")
  .getByText(
    "Publishing failed. Review the channel connection before trying again.",
  )
  .waitFor();
stateChecks.publishFailed = {
  route: "studio",
  status: "failed",
  actionableGuidance: true,
};
screenshots.push(await screenshot("studio-publish-failed"));
const studioErrorOffset = errorResponses.length;
const studioConsoleOffset = consoleErrors.length;
let studioFailureRequests = 0;
await page.route("**/api/v1/studio/brand", (route) => {
  studioFailureRequests += 1;
  return route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code: "brand_unavailable",
        message: "Brand temporarily unavailable",
        details: {},
        request_id: "ui-studio-partial",
      },
    }),
  });
});
await page.reload({ waitUntil: "networkidle" });
await page
  .getByText("Some sections could not be loaded: brand", { exact: true })
  .waitFor();
const preservedCaption = page.getByLabel("Caption 900001", { exact: true });
await preservedCaption.fill("Preserved local merchant edit");
await page.getByRole("button", { name: "Review queue", exact: true }).click();
await page.getByText("Unsaved changes", { exact: true }).waitFor();
await page
  .getByRole("link", { name: failedContentFixture.title, exact: true })
  .click();
assert.equal(
  await preservedCaption.inputValue(),
  "Preserved local merchant edit",
);
await page
  .getByRole("button", { name: "Back to content list", exact: true })
  .click();
await page.getByRole("button", { name: "Post editors", exact: true }).click();
await page.unroute("**/api/v1/studio/brand");
await page.getByRole("button", { name: "Retry unavailable sections" }).click();
await page
  .getByRole("button", { name: "Retry unavailable sections" })
  .waitFor({ state: "detached" });
assert.equal(
  await preservedCaption.inputValue(),
  "Preserved local merchant edit",
);
const studioErrors = errorResponses.splice(studioErrorOffset);
const studioConsole = consoleErrors.splice(studioConsoleOffset);
assert.ok(
  studioFailureRequests > 0 &&
    studioErrors.length === studioFailureRequests &&
    studioErrors.every(
      (response) =>
        response.status === 503 &&
        response.url.endsWith("/api/v1/studio/brand"),
    ),
  `Unexpected Studio failure responses: ${JSON.stringify(studioErrors)}; injected requests: ${studioFailureRequests}`,
);
assert.ok(
  studioConsole.every((message) =>
    message.includes("503 (Service Unavailable)"),
  ),
);
stateChecks.studioPartialFailure = {
  contentPreserved: true,
  retryRecoveredBrand: true,
  unsavedCaptionPreserved: true,
};
screenshots.push(await screenshot("studio-partial-recovered"));
await page.unroute("**/api/v1/studio/content");

// A failed Home source must not hide independently available merchant actions.
const homeErrorOffset = errorResponses.length;
const homeConsoleOffset = consoleErrors.length;
await page.route("**/api/v1/analytics", (route) =>
  route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code: "analytics_unavailable",
        message: "Analytics are temporarily unavailable",
        details: {},
        request_id: "ui-home-partial-failure",
      },
    }),
  }),
);
await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page
  .getByRole("alert")
  .getByText(/Some live store data could not be loaded: response time/)
  .waitFor();
await page.getByText("Conversations awaiting reply", { exact: true }).waitFor();
await page.getByText("Content awaiting review", { exact: true }).waitFor();
await page.getByText("Unavailable", { exact: true }).last().waitFor();
const expectedHomeErrors = errorResponses.splice(homeErrorOffset);
const expectedHomeConsoleErrors = consoleErrors.splice(homeConsoleOffset);
assert.ok(
  expectedHomeErrors.length >= 1 &&
    expectedHomeErrors.every(
      (item) => item.status === 503 && item.url.endsWith("/api/v1/analytics"),
    ),
  `Unexpected Home partial-failure responses: ${JSON.stringify(expectedHomeErrors)}`,
);
assert.ok(
  expectedHomeConsoleErrors.every((message) =>
    message.includes("503 (Service Unavailable)"),
  ),
  `Unexpected Home partial-failure console errors: ${JSON.stringify(expectedHomeConsoleErrors)}`,
);
stateChecks.homePartialFailure = {
  route: "command",
  failedSource: "response time",
  responseCount: expectedHomeErrors.length,
  independentSectionsPreserved: true,
};
screenshots.push(await screenshot("command-partial-failure"));
await page.unroute("**/api/v1/analytics");

await page.goto(`${baseUrl}/app/command`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Command Center" }).waitFor();
const expectedErrorOffset = errorResponses.length;
const expectedConsoleErrorOffset = consoleErrors.length;
await page.route("**/api/v1/products", (route) =>
  route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code: "authentication_required",
        message: "Sign in again",
        details: {},
        request_id: "ui-session-expired",
      },
    }),
  }),
);
await page.goto(`${baseUrl}/app/products`, { waitUntil: "networkidle" });
await page
  .getByText("Your session expired. Sign in again to continue.")
  .waitFor();
assert.ok(
  page.url().endsWith("/login?reason=session-expired"),
  `Unexpected expired-session URL: ${page.url()}`,
);
const expectedSessionErrors = errorResponses.splice(expectedErrorOffset);
const expectedSessionConsoleErrors = consoleErrors.splice(
  expectedConsoleErrorOffset,
);
assert.ok(
  expectedSessionErrors.length >= 1 &&
    expectedSessionErrors.every(
      (item) => item.status === 401 && item.url.endsWith("/api/v1/products"),
    ),
  `Unexpected session-expiration responses: ${JSON.stringify(expectedSessionErrors)}`,
);
assert.ok(
  expectedSessionConsoleErrors.length >= 1 &&
    expectedSessionConsoleErrors.every((message) =>
      message.includes("401 (Unauthorized)"),
    ),
  `Unexpected session-expiration console errors: ${JSON.stringify(expectedSessionConsoleErrors)}`,
);
stateChecks.sessionExpired = {
  redirectedToLogin: true,
  responseCount: expectedSessionErrors.length,
  consoleErrorCount: expectedSessionConsoleErrors.length,
};
screenshots.push(await screenshot("login-session-expired"));
await page.unroute("**/api/v1/products");

await browser.close();

const result = {
  public: publicChecks.map((check) => ({
    ...check,
    overflow: check.bodyWidth > check.viewportWidth + 1,
  })),
  routes: routeChecks,
  tablet: {
    ...tabletDimensions,
    overflow: tabletDimensions.bodyWidth > tabletDimensions.viewportWidth + 1,
  },
  mobile: {
    ...mobileDimensions,
    overflow: mobileDimensions.bodyWidth > mobileDimensions.viewportWidth + 1,
  },
  states: stateChecks,
  screenshots,
  consoleErrors,
  pageErrors,
  failedRequests,
  errorResponses,
};
console.log(JSON.stringify(result, null, 2));

if (
  consoleErrors.length ||
  pageErrors.length ||
  failedRequests.length ||
  errorResponses.length ||
  result.public.some(
    (check) => check.overflow || check.accessibilityIssues.length,
  ) ||
  routeChecks.some((check) => check.overflow) ||
  routeChecks.some((check) => check.accessibilityIssues.length) ||
  result.tablet.overflow ||
  result.mobile.overflow ||
  !result.mobile.mobileNavVisible ||
  screenshots.some((item) => item.bytes < 10_000)
) {
  process.exitCode = 1;
}
