import type { StoreSettings, StoreSettingsInput } from "../../lib/types";

export function editableStoreSettings(
  settings: StoreSettings,
): StoreSettingsInput {
  return {
    store_name: settings.store_name,
    default_language: settings.default_language,
    business_type: settings.business_type,
    logo_url: settings.logo_url,
    brand_colors: settings.brand_colors,
    tone: settings.tone,
    assistant_name: settings.assistant_name,
    assistant_instructions: settings.assistant_instructions,
    shipping_policy: settings.shipping_policy,
    return_policy: settings.return_policy,
    ai_monthly_budget: settings.ai_monthly_budget,
  };
}

export function storeSettingsChanged(
  current: StoreSettings | null,
  saved: StoreSettings | null,
): boolean {
  if (!current || !saved) return false;
  return (
    JSON.stringify(editableStoreSettings(current)) !==
    JSON.stringify(editableStoreSettings(saved))
  );
}
