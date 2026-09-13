import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const baseUrl = process.env.UI_BASE_URL ?? "http://127.0.0.1:5173";
const demoPassword = process.env.UI_DEMO_PASSWORD;
if (!demoPassword) {
  throw new Error(
    "UI_DEMO_PASSWORD is required; use the one-time password printed by scripts.bootstrap_env",
  );
}

const browser = await chromium.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
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
    errorResponses.push(`${response.status()} ${response.url()}`);
  }
});

async function waitForContentStatus(contentId, expectedStatus) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const persisted = await page.evaluate(
      async ({ id, status }) => {
        const response = await globalThis.fetch("/api/v1/studio/content", {
          credentials: "include",
        });
        if (!response.ok) throw new Error("Could not poll content status");
        const items = await response.json();
        return items.some((item) => item.id === id && item.status === status);
      },
      { id: contentId, status: expectedStatus },
    );
    if (persisted) {
      await page
        .getByRole("button", { name: "Refresh delivery status" })
        .click();
      const card = page.locator("article.content-card").filter({
        has: page.locator(`textarea[aria-label="Caption ${contentId}"]`),
      });
      await card.waitFor();
      await card.locator(`[data-content-status="${expectedStatus}"]`).waitFor();
      return card;
    }
    await page.waitForTimeout(500);
  }
  throw new Error(
    `Content ${contentId} did not reach expected status ${expectedStatus}`,
  );
}

async function submitAndRequireSuccess(button, requestPath) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (candidate) =>
        candidate.url().includes(requestPath) &&
        candidate.request().method() === "PUT",
    ),
    button.click(),
  ]);
  assert.equal(
    response.status(),
    200,
    `${requestPath} did not persist successfully`,
  );
}

try {
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await page.evaluate(() =>
    window.localStorage.setItem("commerce-language", "en"),
  );
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Email", { exact: true }).fill("merchant@example.com");
  await page.getByLabel("Password", { exact: true }).fill(demoPassword);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/app/command");
  await page.getByRole("heading", { name: "Command Center" }).waitFor();

  // Anonymous session checks before login may return 401 by design.
  consoleErrors.length = 0;
  errorResponses.length = 0;

  await page.goto(`${baseUrl}/app/settings`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Store settings" }).waitFor();
  const storeLabels = await page.locator("main label").allTextContents();
  assert.ok(
    storeLabels.some((label) => label.includes("Shipping policy")),
    `English store profile labels are incomplete: ${JSON.stringify(storeLabels)}`,
  );
  const storeName = page.getByLabel("Store name", { exact: true });
  const shippingPolicy = page.getByLabel("Shipping policy");
  const originalStoreName = await storeName.inputValue();
  const originalShippingPolicy = await shippingPolicy.inputValue();
  await storeName.fill("Browser-verified store profile");
  await shippingPolicy.fill("Browser-verified shipping policy.");
  await submitAndRequireSuccess(
    page.getByRole("button", { name: "Save settings", exact: true }),
    "/api/v1/settings/store",
  );
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(
    await page.getByLabel("Store name", { exact: true }).inputValue(),
    "Browser-verified store profile",
    "Store profile name did not survive a reload",
  );
  assert.equal(
    await page.getByLabel("Shipping policy").inputValue(),
    "Browser-verified shipping policy.",
    "Store policy did not survive a reload",
  );
  await page.getByLabel("Store name", { exact: true }).fill(originalStoreName);
  await page.getByLabel("Shipping policy").fill(originalShippingPolicy);
  await submitAndRequireSuccess(
    page.getByRole("button", { name: "Save settings", exact: true }),
    "/api/v1/settings/store",
  );

  await page.goto(`${baseUrl}/app/studio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Content studio" }).waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Generate draft", exact: true })
      .count(),
    0,
    "Draft creator should not displace the review queue until requested",
  );
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Brand voice", exact: true }).click();
  const brandAudience = page.getByLabel("Audience");
  const brandGuidelines = page.getByLabel("Writing guidelines");
  const originalAudience = await brandAudience.inputValue();
  const originalGuidelines = await brandGuidelines.inputValue();
  await brandAudience.fill("Browser-verified merchant audience");
  await brandGuidelines.fill("Use factual catalog claims only.");
  await submitAndRequireSuccess(
    page.getByRole("button", { name: "Save brand voice", exact: true }),
    "/api/v1/studio/brand",
  );
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Brand voice", exact: true }).click();
  assert.equal(
    await page.getByLabel("Audience").inputValue(),
    "Browser-verified merchant audience",
    "Brand audience did not survive a reload",
  );
  assert.equal(
    await page.getByLabel("Writing guidelines").inputValue(),
    "Use factual catalog claims only.",
    "Brand guidelines did not survive a reload",
  );
  await page.getByLabel("Audience").fill(originalAudience);
  await page.getByLabel("Writing guidelines").fill(originalGuidelines);
  await submitAndRequireSuccess(
    page.getByRole("button", { name: "Save brand voice", exact: true }),
    "/api/v1/studio/brand",
  );

  await page.goto(`${baseUrl}/app/inbox`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Inbox", exact: true }).waitFor();
  const conversations = page.locator("button.conversation-row");
  assert.ok((await conversations.count()) > 0, "No seeded conversation found");
  const conversationId = await page.evaluate(async () => {
    const response = await globalThis.fetch("/api/v1/inbox/conversations", {
      credentials: "include",
    });
    if (!response.ok)
      throw new Error("Could not load conversations for E2E proof");
    const payload = await response.json();
    return payload.conversations[0].id;
  });
  await conversations.first().click();
  const reply = page.getByLabel("Reply text");
  await reply.waitFor();
  const customerContext = page.getByLabel("Customer & commerce context");
  await customerContext.waitFor();
  await customerContext.locator(".inbox-context__metrics").waitFor();
  await customerContext
    .getByRole("link", { name: "Open customer profile" })
    .waitFor();
  await page.getByRole("button", { name: "Smart suggestion" }).click();
  const citations = page.getByLabel("Grounding citations");
  await citations.waitFor();
  const citationCount = await citations.locator("code").count();
  assert.ok(citationCount > 0, "Grounded suggestion has no citations");
  const replyText = await reply.inputValue();
  assert.ok(
    replyText.trim().length > 0,
    "Grounded suggestion did not fill reply text",
  );
  const outboundBefore = await page.locator(".bubble--out").count();
  await page.getByRole("button", { name: "Send", exact: true }).click();
  let persistedOutbound = null;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    persistedOutbound = await page.evaluate(
      async ({ id, expectedCount }) => {
        const response = await globalThis.fetch(
          `/api/v1/inbox/conversations/${id}`,
          {
            credentials: "include",
          },
        );
        if (!response.ok)
          throw new Error("Could not poll conversation delivery");
        const detail = await response.json();
        const outbound = detail.messages.filter(
          (message) => message.direction === "outbound",
        );
        const newest = outbound.at(-1);
        return outbound.length === expectedCount && newest?.status === "sent"
          ? newest
          : null;
      },
      { id: conversationId, expectedCount: outboundBefore + 1 },
    );
    if (persistedOutbound) break;
    await page.waitForTimeout(500);
  }
  assert.ok(persistedOutbound, "New outbound message did not persist as sent");
  await page.reload({ waitUntil: "networkidle" });
  await page.locator("button.conversation-row").first().click();
  await reply.waitFor();
  const newOutbound = page.locator(".bubble--out").nth(outboundBefore);
  await newOutbound.waitFor({ timeout: 15_000 });
  await newOutbound
    .locator("small", { hasText: "Sent \u2713" })
    .waitFor({ timeout: 15_000 });
  const outboundAfter = await page.locator(".bubble--out").count();
  assert.equal(
    outboundAfter,
    outboundBefore + 1,
    "Reply was not recorded exactly once",
  );

  await page.goto(`${baseUrl}/app/studio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Content studio" }).waitFor();
  await page.locator('p[aria-live="polite"]', { hasText: "posts" }).waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Generate draft", exact: true })
      .count(),
    0,
    "Draft creator should not displace the review queue until requested",
  );
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Post editors", exact: true }).click();
  const cardsBefore = await page.locator("article.content-card").count();
  await page.getByRole("button", { name: "Generate draft" }).click();
  await page.getByText("Draft created and product facts checked.").waitFor();
  const cards = page.locator("article.content-card");
  await cards
    .nth(cardsBefore)
    .waitFor()
    .catch(async () => cards.first().waitFor());
  assert.equal(
    await cards.count(),
    cardsBefore + 1,
    "One draft was not created",
  );
  const draftCard = cards.filter({ hasText: "draft" }).first();
  const caption = draftCard.locator('textarea[aria-label^="Caption "]');
  const captionLabel = await caption.getAttribute("aria-label");
  assert.ok(captionLabel, "Generated draft has no stable caption label");
  const contentId = Number(captionLabel.replace("Caption ", ""));
  assert.ok(Number.isInteger(contentId), "Generated draft ID is invalid");
  const originalCaption = await caption.inputValue();
  await caption.fill(`${originalCaption} Reviewed by merchant.`);
  assert.equal(
    await draftCard
      .getByRole("button", { name: "Approve", exact: true })
      .isDisabled(),
    true,
  );
  assert.equal(
    await draftCard
      .getByRole("button", { name: "Regenerate caption" })
      .isDisabled(),
    true,
  );
  await page.getByRole("button", { name: "Refresh delivery status" }).click();
  assert.equal(
    await caption.inputValue(),
    `${originalCaption} Reviewed by merchant.`,
  );
  await draftCard.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByText("save completed.", { exact: true }).waitFor();
  const reviewTitle = await draftCard.locator("h3").innerText();
  await page.getByRole("searchbox").fill(reviewTitle);
  await draftCard.getByRole("link", { name: reviewTitle, exact: true }).click();
  assert.equal(
    new URL(page.url()).searchParams.get("content"),
    String(contentId),
  );
  await page.getByRole("button", { name: "Back to content list" }).click();
  assert.equal(await page.getByRole("searchbox").inputValue(), reviewTitle);
  await page.getByRole("searchbox").fill("");

  let currentCard = page
    .locator("article.content-card")
    .filter({ has: page.getByLabel(`Caption ${contentId}`) });
  await currentCard
    .getByRole("button", { name: "Approve", exact: true })
    .click();
  await page.getByText("approve completed.", { exact: true }).waitFor();
  currentCard = page
    .locator("article.content-card")
    .filter({ has: page.getByLabel(`Caption ${contentId}`) });
  await currentCard
    .getByRole("button", { name: "Publish", exact: true })
    .click();
  await page
    .getByText(
      "Publication request accepted. Refresh delivery status for the worker result; this is not confirmation of publication.",
      { exact: true },
    )
    .waitFor();
  await waitForContentStatus(contentId, "published");

  assert.deepEqual(consoleErrors, [], "Browser console errors were detected");
  assert.deepEqual(pageErrors, [], "Browser page errors were detected");
  assert.deepEqual(failedRequests, [], "Failed browser requests were detected");
  assert.deepEqual(errorResponses, [], "HTTP error responses were detected");

  console.log(
    JSON.stringify({
      sales: {
        citation_count: citationCount,
        outbound_messages_added: outboundAfter - outboundBefore,
        final_status: "sent",
      },
      content: {
        drafts_added: 1,
        merchant_edit_saved: true,
        approval_recorded: true,
        unsaved_approval_blocked: true,
        refresh_preserves_edits: true,
        review_link_retains_search: true,
        delivery_refresh_verified: true,
        final_status: "published",
      },
      profiles: {
        store_saved_and_reloaded: true,
        brand_saved_and_reloaded: true,
        original_values_restored: true,
      },
      browser_errors: 0,
    }),
  );
} finally {
  await browser.close();
}
