export type ContentStatusPresentation = {
  label: string;
  tone: "neutral" | "success" | "warning" | "error";
  guidance: string | null;
};

const presentations: Record<
  string,
  Record<"ar" | "en", ContentStatusPresentation>
> = {
  draft: {
    ar: { label: "مسودة", tone: "warning", guidance: null },
    en: { label: "Draft", tone: "warning", guidance: null },
  },
  approved: {
    ar: { label: "معتمد", tone: "warning", guidance: null },
    en: { label: "Approved", tone: "warning", guidance: null },
  },
  scheduled: {
    ar: { label: "مجدول", tone: "warning", guidance: null },
    en: { label: "Scheduled", tone: "warning", guidance: null },
  },
  publishing: {
    ar: { label: "جارٍ النشر…", tone: "warning", guidance: null },
    en: { label: "Publishing…", tone: "warning", guidance: null },
  },
  published: {
    ar: { label: "منشور", tone: "success", guidance: null },
    en: { label: "Published", tone: "success", guidance: null },
  },
  partial: {
    ar: {
      label: "نشر جزئي",
      tone: "warning",
      guidance:
        "اكتمل النشر على بعض القنوات فقط. راجع نتائج القنوات قبل المحاولة مجددًا.",
    },
    en: {
      label: "Partially published",
      tone: "warning",
      guidance:
        "Publishing completed on only some channels. Review channel results before retrying.",
    },
  },
  failed: {
    ar: {
      label: "فشل النشر",
      tone: "error",
      guidance: "فشل النشر. راجع اتصال القناة قبل المحاولة مجددًا.",
    },
    en: {
      label: "Publish failed",
      tone: "error",
      guidance:
        "Publishing failed. Review the channel connection before trying again.",
    },
  },
  publish_retrying: {
    ar: {
      label: "إعادة محاولة النشر مجدولة",
      tone: "warning",
      guidance: "فشل النشر مؤقتًا. تمت جدولة إعادة المحاولة تلقائيًا.",
    },
    en: {
      label: "Publish retry scheduled",
      tone: "warning",
      guidance:
        "Publishing failed temporarily. The worker will retry automatically.",
    },
  },
  publish_unknown: {
    ar: {
      label: "حالة النشر غير مؤكدة",
      tone: "error",
      guidance: "راجع القناة الاجتماعية قبل النشر مجددًا لمنع تكرار المنشور.",
    },
    en: {
      label: "Publish status unknown",
      tone: "error",
      guidance:
        "Review the social channel before publishing again to avoid a duplicate post.",
    },
  },
};

export function contentStatusPresentation(
  status: string,
  language: "ar" | "en",
): ContentStatusPresentation {
  return (
    presentations[status]?.[language] ?? {
      label: status.replaceAll("_", " "),
      tone: "neutral",
      guidance: null,
    }
  );
}
