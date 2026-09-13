const locale = (language: string) =>
  language === "ar" ? "ar-EG-u-nu-latn" : "en-US";

export function formatNumber(value: number | string, language: string): string {
  const numeric = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(numeric)) return String(value);
  return new Intl.NumberFormat(locale(language), {
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function formatMoney(value: number | string, language: string): string {
  const numeric = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(numeric)) return String(value);
  const amount = new Intl.NumberFormat(locale(language), {
    maximumFractionDigits: numeric >= 1000 ? 0 : 2,
  }).format(numeric);
  return language === "ar" ? `${amount} ج.م` : `EGP ${amount}`;
}

export function formatDateTime(iso: string, language: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(language === "ar" ? "ar-EG-u-nu-latn" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Keep minor units and the authoritative currency when showing transaction/catalog amounts. */
export function formatCurrency(
  value: number | string,
  language: string,
  currency = "EGP",
): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${value} ${currency}`;
  return `${new Intl.NumberFormat(locale(language), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric)} ${currency}`;
}
