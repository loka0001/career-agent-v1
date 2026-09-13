export function integrationReadinessPresentation(
  configured: boolean,
  mode: string,
  language: "ar" | "en",
): { label: string; tone: "success" | "warning" | "error" } {
  if (configured) {
    return {
      label: language === "ar" ? "جاهز" : "Ready",
      tone: "success",
    };
  }
  if (mode === "disconnected") {
    return {
      label: language === "ar" ? "مفصول" : "Disconnected",
      tone: "error",
    };
  }
  if (mode === "action_required" || mode === "expired") {
    return {
      label: language === "ar" ? "يحتاج إجراء" : "Action required",
      tone: "error",
    };
  }
  if (mode === "degraded" || mode === "partial") {
    return {
      label: language === "ar" ? "اتصال ضعيف" : "Connection degraded",
      tone: "warning",
    };
  }
  return {
    label: language === "ar" ? "غير مهيأ" : "Not configured",
    tone: "error",
  };
}
