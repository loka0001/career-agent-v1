import type { MessageStatus } from "../../lib/types";

export function messageStatusLabel(
  status: MessageStatus,
  language: "ar" | "en",
): string {
  if (status === "sent") return language === "ar" ? "أُرسلت ✓" : "Sent ✓";
  if (status === "queued" || status === "sending") {
    return language === "ar" ? "في الطريق…" : "Sending…";
  }
  if (status === "failed")
    return language === "ar" ? "فشل الإرسال" : "Send failed";
  if (status === "delivery_unknown") {
    return language === "ar"
      ? "حالة التسليم غير مؤكدة — راجع القناة قبل إعادة الإرسال"
      : "Delivery unknown — review the channel before resending";
  }
  return status;
}
