type SupportedLanguage = "ar" | "en";

const copy = {
  ar: {
    store: {
      storeName: "اسم المتجر",
      businessType: "نوع النشاط",
      defaultLanguage: "اللغة",
      aiBudget: "ميزانية AI الشهرية بالدولار",
      logoUrl: "رابط الشعار",
      primaryColor: "اللون الأساسي",
      accentColor: "لون التمييز",
      shippingPolicy: "سياسة الشحن",
      returnPolicy: "سياسة الاسترجاع",
      save: "حفظ الإعدادات",
      saved: "تم حفظ إعدادات المتجر والسياسات.",
      businessTypes: {
        retail: "تجارة تجزئة",
        fashion: "أزياء",
        beauty: "تجميل",
        electronics: "إلكترونيات",
        food: "أغذية",
        services: "خدمات",
      },
    },
    brand: {
      tone: "نبرة البراند",
      primaryColor: "اللون الأساسي",
      audience: "الجمهور",
      guidelines: "قواعد الكتابة",
      save: "حفظ صوت البراند",
      saved: "تم حفظ صوت البراند.",
    },
    agent: {
      title: "إعدادات مساعد المبيعات",
      description:
        "شخصية المساعد وتعليماته، مع اختبار مباشر على كتالوج المتجر.",
      loading: "جارٍ تحميل المساعد…",
      savedStatus: "كل التغييرات محفوظة",
      unsavedStatus: "تغييرات غير محفوظة",
      discard: "تجاهل التغييرات",
      personaTitle: "شخصية المساعد",
      personaDescription: "اضبط الاسم والنبرة والقواعد التي تحكم ردود المساعد.",
      assistantName: "اسم المساعد",
      tone: "نبرة الرد",
      instructions: "تعليمات خاصة",
      instructionsPlaceholder:
        "مثال: ابدأ بالسؤال عن الميزانية، ولا تعرض خصماً غير موجود.",
      save: "حفظ شخصية المساعد",
      saved: "تم حفظ شخصية المساعد.",
      testTitle: "اختبار المساعد",
      testDescription:
        "جرّب سؤالاً كما يكتبه العميل وراجع الرد المبني على بيانات المنتجات.",
      realCatalogData: "بيانات الكتالوج الحقيقية",
      testMessage: "رسالة اختبار المساعد",
      runTest: "تشغيل الاختبار",
      runningTest: "جارٍ الاختبار…",
      defaultTestMessage: "أريد منتجاً مناسباً بميزانية 1500 جنيه",
      tones: {
        friendly: "ودود",
        professional: "احترافي",
        concise: "مختصر",
        luxury: "فاخر",
      },
    },
  },
  en: {
    store: {
      storeName: "Store name",
      businessType: "Business type",
      defaultLanguage: "Language",
      aiBudget: "Monthly AI budget in USD",
      logoUrl: "Logo URL",
      primaryColor: "Primary color",
      accentColor: "Accent color",
      shippingPolicy: "Shipping policy",
      returnPolicy: "Return policy",
      save: "Save settings",
      saved: "Store settings and policies saved.",
      businessTypes: {
        retail: "Retail",
        fashion: "Fashion",
        beauty: "Beauty",
        electronics: "Electronics",
        food: "Food",
        services: "Services",
      },
    },
    brand: {
      tone: "Brand tone",
      primaryColor: "Primary color",
      audience: "Audience",
      guidelines: "Writing guidelines",
      save: "Save brand voice",
      saved: "Brand voice saved.",
    },
    agent: {
      title: "Sales assistant settings",
      description:
        "Assistant persona and instructions, with a live catalog-grounded test.",
      loading: "Loading assistant…",
      savedStatus: "All changes saved",
      unsavedStatus: "Unsaved changes",
      discard: "Discard changes",
      personaTitle: "Assistant persona",
      personaDescription:
        "Set the name, tone, and rules that govern assistant replies.",
      assistantName: "Assistant name",
      tone: "Reply tone",
      instructions: "Special instructions",
      instructionsPlaceholder:
        "Example: Ask about budget first, and never offer a discount that does not exist.",
      save: "Save assistant persona",
      saved: "Assistant persona saved.",
      testTitle: "Test assistant",
      testDescription:
        "Ask a customer-style question and review the catalog-grounded reply.",
      realCatalogData: "Real catalog data",
      testMessage: "Assistant test message",
      runTest: "Run test",
      runningTest: "Testing…",
      defaultTestMessage:
        "I need a suitable product within a 1,500 EGP budget.",
      tones: {
        friendly: "Friendly",
        professional: "Professional",
        concise: "Concise",
        luxury: "Luxury",
      },
    },
  },
} as const;

export function profileCopy(language: SupportedLanguage) {
  return copy[language];
}
