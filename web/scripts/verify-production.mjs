import { mkdir, stat } from "node:fs/promises";
import { chromium } from "playwright-core";

const baseUrl =
  process.env.UI_BASE_URL ?? "https://commerce-revenue-autopilot.vercel.app";
const merchantEmail =
  process.env.PRODUCTION_MERCHANT_EMAIL ?? "merchant@example.com";
const merchantPassword = process.env.PRODUCTION_MERCHANT_PASSWORD;
if (!merchantPassword) {
  throw new Error(
    "PRODUCTION_MERCHANT_PASSWORD is required for authenticated production verification.",
  );
}
const outputDirectory = new URL(
  "../../artifacts/production-verification/",
  import.meta.url,
);
await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  colorScheme: "dark",
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
    errorResponses.push({ status: response.status(), url: response.url() });
  }
});

async function screenshot(name) {
  const path = new URL(`${name}.png`, outputDirectory);
  await page.screenshot({ path: path.pathname.slice(1), fullPage: true });
  const info = await stat(path);
  return { name, bytes: info.size };
}

async function navigateApp(route) {
  await page.goto(`${baseUrl}/app/${route}`, {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await page.locator(".page-heading h1").waitFor({ timeout: 60_000 });
  await page.waitForTimeout(750);
}

await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
const initialState = {
  url: page.url(),
  title: await page.title(),
  bodyText: (await page.locator("body").innerText()).slice(0, 1000),
};
console.log(JSON.stringify({ initialState }, null, 2));
await screenshot("login-initial");
await page.locator('input[type="email"]').waitFor();
const loginPage = {
  url: page.url(),
  title: await page.title(),
  direction: await page.locator("html").getAttribute("dir"),
  hasArabicHeading: await page
    .getByRole("heading", { name: "دخول مساحة العمل" })
    .isVisible(),
};
const screenshots = [await screenshot("login-desktop")];

await page.locator('input[type="email"]').fill(merchantEmail);
await page.locator('input[type="password"]').fill(merchantPassword);
const loginResponsePromise = page.waitForResponse(
  (response) =>
    response.url().endsWith("/api/v1/auth/login") &&
    response.request().method() === "POST",
);
await page.locator('button[type="submit"]').click();
const loginResponse = await loginResponsePromise;
await page.waitForURL("**/app/command", { timeout: 30_000 });
await page.locator(".page-heading h1").waitFor();
consoleErrors.length = 0;
errorResponses.length = 0;

const routes = [
  "command",
  "inbox",
  "opportunities",
  "customers",
  "products",
  "products/new",
  "orders",
  "studio",
  "calendar",
  "analytics",
  "automations",
  "integrations",
  "agent-settings",
  "team",
  "billing",
  "settings",
  "security",
  "api-keys",
  "onboarding",
  "privacy",
];
const routeChecks = [];
for (const route of routes) {
  await navigateApp(route);
  routeChecks.push(
    await page.evaluate((currentRoute) => {
      const heading = document.querySelector(".page-heading h1");
      return {
        route: currentRoute,
        heading: heading?.textContent?.trim() ?? "",
        bodyWidth: document.body.scrollWidth,
        viewportWidth: window.innerWidth,
        overflow: document.body.scrollWidth > window.innerWidth + 1,
      };
    }, route),
  );
}

await navigateApp("command");
screenshots.push(await screenshot("command-desktop"));
await navigateApp("inbox");
const productionInbox = {
  hasSimulationControl: await page
    .getByText("محاكاة رسالة عميل", { exact: false })
    .isVisible()
    .catch(() => false),
};
await navigateApp("billing");
const productionBilling = {
  planCards: await page.locator(".plan-card").count(),
  hasCardInput:
    (await page.locator('input[autocomplete="cc-number"]').count()) > 0,
};
await page.evaluate(() =>
  globalThis.localStorage.setItem("commerce-language", "en"),
);
await navigateApp("command");
const english = {
  direction: await page.locator("html").getAttribute("dir"),
  heading: await page.locator(".page-heading h1").innerText(),
};
await page.setViewportSize({ width: 390, height: 844 });
await navigateApp("command");
const mobile = await page.evaluate(() => ({
  bodyWidth: document.body.scrollWidth,
  viewportWidth: window.innerWidth,
  overflow: document.body.scrollWidth > window.innerWidth + 1,
  mobileNavVisible:
    getComputedStyle(document.querySelector(".mobile-nav")).display !== "none",
}));
screenshots.push(await screenshot("command-mobile"));

await browser.close();

const result = {
  baseUrl,
  loginPage,
  loginStatus: loginResponse.status(),
  routeChecks,
  productionInbox,
  productionBilling,
  english,
  mobile,
  screenshots,
  consoleErrors,
  pageErrors,
  failedRequests,
  errorResponses,
};
console.log(JSON.stringify(result, null, 2));

if (
  loginResponse.status() !== 200 ||
  !loginPage.hasArabicHeading ||
  loginPage.direction !== "rtl" ||
  routeChecks.some((check) => check.overflow || !check.heading) ||
  productionInbox.hasSimulationControl ||
  productionBilling.planCards ||
  productionBilling.hasCardInput ||
  english.direction !== "ltr" ||
  english.heading !== "Command Center" ||
  mobile.overflow ||
  !mobile.mobileNavVisible ||
  screenshots.some((item) => item.bytes < 10_000) ||
  consoleErrors.length ||
  pageErrors.length ||
  failedRequests.length ||
  errorResponses.length
) {
  process.exitCode = 1;
}
