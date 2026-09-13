import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright-core";

const baseUrl = process.env.UI_BASE_URL ?? "http://127.0.0.1:5173";
if (!process.env.UI_DEMO_PASSWORD)
  throw new Error(
    "UI_DEMO_PASSWORD is required for isolated demo verification",
  );
const evidence = new URL("../../artifacts/ui-calendar/", import.meta.url);
await mkdir(evidence, { recursive: true });
const browser = await chromium.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  timezoneId: "Africa/Cairo",
});
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
page.on("requestfailed", (request) =>
  errors.push(
    `${request.method()} ${request.url()}: ${request.failure()?.errorText}`,
  ),
);
page.on("response", (response) => {
  if (response.status() >= 400)
    errors.push(`${response.status()} ${response.url()}`);
});
let year = new Date().getFullYear() + 1;
const ids = [];
const screenshots = [];
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
  errors.length = 0; // Anonymous pre-login session checks may return 401.
  const occupiedYears = await page.evaluate(async () => {
    const response = await globalThis.fetch("/api/v1/studio/content");
    if (!response.ok) throw new Error("Calendar source unavailable");
    return (await response.json())
      .filter((item) => item.scheduled_for)
      .map((item) => Number(item.scheduled_for.slice(0, 4)));
  });
  while (occupiedYears.includes(year)) year += 1;
  const date = `${year}-01-31`;
  await page.goto(`${baseUrl}/app/studio`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await page.getByRole("button", { name: "Post editors", exact: true }).click();
  await page.getByLabel("Schedule", { exact: true }).fill(`${date}T12:00`);
  for (let index = 0; index < 4; index += 1) {
    await page
      .getByLabel("Platform", { exact: true })
      .selectOption(index === 3 ? "facebook" : "instagram");
    const [response] = await Promise.all([
      page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname ===
            "/api/v1/studio/content/generate" &&
          response.request().method() === "POST",
      ),
      page.getByRole("button", { name: "Generate draft" }).click(),
    ]);
    assert.equal(response.status(), 201, await response.text());
    const item = await response.json();
    assert.equal(
      item.status,
      "draft",
      "Calendar setup must not approve or publish content",
    );
    ids.push(item.id);
    await page.getByLabel(`Caption ${item.id}`, { exact: true }).waitFor();
  }
  await page.goto(`${baseUrl}/app/calendar?view=month&date=${date}`, {
    waitUntil: "networkidle",
  });
  await page
    .getByRole("button", { name: "+1 View all", exact: true })
    .waitFor();
  assert.equal(await page.locator("a.campaign-chip").count(), 3);
  await page.getByRole("button", { name: "Next period" }).click();
  assert.equal(new URL(page.url()).searchParams.get("date"), `${year}-02-01`);
  await page.goto(`${baseUrl}/app/calendar?view=month&date=${date}`, {
    waitUntil: "networkidle",
  });
  await page.getByRole("button", { name: "+1 View all", exact: true }).click();
  assert.equal(new URL(page.url()).searchParams.get("view"), "agenda");
  await page.locator("article.calendar-item").first().waitFor();
  assert.equal(await page.locator("article.calendar-item").count(), 4);
  assert.match(
    await page.locator("article.calendar-item small").first().innerText(),
    /12:00/,
    "Noon entered in Africa/Cairo must remain noon after API reload",
  );
  const returnedSchedules = await page.evaluate(async (ids) => {
    const response = await globalThis.fetch("/api/v1/studio/content");
    if (!response.ok) throw new Error("Could not verify stored schedule");
    return (await response.json())
      .filter((item) => ids.includes(item.id))
      .map((item) => item.scheduled_for);
  }, ids);
  assert.equal(returnedSchedules.length, 4);
  assert.ok(
    returnedSchedules.every((value) => /(?:Z|[+-]\d{2}:\d{2})$/.test(value)),
    "API schedules must have explicit timezone offsets",
  );
  await page.getByRole("button", { name: "Next period" }).click();
  await page
    .getByText("No content scheduled in this period", { exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Previous period" }).click();
  await page.getByLabel("Filter by platform").selectOption("facebook");
  await page.waitForURL(
    (url) => url.searchParams.get("platform") === "facebook",
  );
  await page.reload({ waitUntil: "networkidle" });
  await page.locator("article.calendar-item").first().waitFor();
  assert.equal(await page.locator("article.calendar-item").count(), 1);
  await page.locator(`a[href="/app/studio?content=${ids[3]}"]`).click();
  await page.getByLabel(`Caption ${ids[3]}`, { exact: true }).waitFor();
  assert.equal(
    await page.getByRole("button", { name: "Generate draft" }).count(),
    0,
  );
  await page.goBack({ waitUntil: "networkidle" });
  assert.equal(new URL(page.url()).searchParams.get("platform"), "facebook");
  await page.getByRole("link", { name: "New campaign", exact: true }).click();
  await page.getByLabel("Campaign name", { exact: true }).waitFor();

  for (const language of ["en", "ar"]) {
    await page.evaluate(
      (language) => window.localStorage.setItem("commerce-language", language),
      language,
    );
    for (const [width, view] of [
      [1440, "month"],
      [768, "week"],
      [390, "agenda"],
    ]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(`${baseUrl}/app/calendar?view=${view}&date=${date}`, {
        waitUntil: "networkidle",
      });
      await page
        .locator(
          view === "month" ? "a.campaign-chip" : "article.calendar-item a",
        )
        .first()
        .waitFor();
      assert.equal(
        await page.locator("html").getAttribute("dir"),
        language === "ar" ? "rtl" : "ltr",
      );
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
        `${language} ${width} page overflow`,
      );
      assert.equal(await page.locator("vite-error-overlay").count(), 0);
      const name = `calendar-${language}-${view}-${width}.png`;
      await page.screenshot({
        path: new URL(name, evidence).pathname.replace(/^\/([A-Za-z]:)/, "$1"),
        fullPage: true,
      });
      screenshots.push(name);
    }
  }
  assert.deepEqual(errors, [], "Unexpected browser/network errors");
  console.log(
    JSON.stringify({
      calendar: {
        real_dated_drafts_created: ids.length,
        approval_not_bypassed: true,
        month_end_navigation: true,
        overflow_agenda: true,
        period_navigation: true,
        platform_reload: true,
        review_link: true,
        campaign_builder_link: true,
      },
      screenshots,
      unexpected_errors: 0,
    }),
  );
} finally {
  await browser.close();
}
