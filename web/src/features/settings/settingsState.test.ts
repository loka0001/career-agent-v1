import type { StoreSettings } from "../../lib/types";
import { editableStoreSettings, storeSettingsChanged } from "./settingsState";

const settings: StoreSettings = {
  store_id: "demo-store",
  slug: "demo-store",
  store_name: "Demo Store",
  default_language: "en",
  business_type: "retail",
  logo_url: null,
  brand_colors: { primary: "#2563eb", accent: "#14b8a6" },
  tone: "friendly",
  assistant_name: "Sales assistant",
  assistant_instructions: "Use catalog facts.",
  shipping_policy: "Ships in two days.",
  return_policy: "Returns in 14 days.",
  ai_monthly_budget: "25.00",
  onboarding_steps: {},
  onboarding_completed: false,
  updated_at: "2026-09-10T00:00:00Z",
};

describe("store settings edit state", () => {
  it("ignores server metadata when building a save payload", () => {
    expect(editableStoreSettings(settings)).not.toHaveProperty("updated_at");
    expect(editableStoreSettings(settings).store_name).toBe("Demo Store");
  });

  it("detects merchant edits but not an unchanged server snapshot", () => {
    expect(storeSettingsChanged(settings, { ...settings })).toBe(false);
    expect(
      storeSettingsChanged(
        { ...settings, store_name: "Edited Store" },
        settings,
      ),
    ).toBe(true);
    expect(storeSettingsChanged(null, settings)).toBe(false);
  });
});
