import type { MarketingStatus } from "../../lib/types";

const english = {
  steps: ["Data & image", "Review facts", "Content", "Approve & publish"],
  eyebrow: "Product workflow",
  title: "Add and publish a product",
  intro:
    "Four steps: your data, review, content, then explicit approval before publishing.",
  running: "Running this step…",
  unexpectedError: "An unexpected error occurred. Try this step again.",
  requestFailed: "The request could not be completed",
  analysisReady: "Analysis is ready. Review the facts before activation.",
  activated: "The product is active and saved in the knowledge base.",
  contentReady: "Two platform versions are ready. You can edit them.",
  contentSaved: "Changes saved. Any previous approval has been cleared.",
  approved: "Your approval and its time have been recorded.",
  publishFinished:
    "The publishing attempt has finished. Check each platform result below. Retrying this request will not create a duplicate post.",
  confirmPublish: "Confirm publishing to Facebook and Instagram?",
  dataTitle: "1. Product data and image",
  dataHint:
    "AI analyzes the image and proposes visible facts — you remain the approver.",
  productId: "Product ID",
  productIdHint: "Letters, numbers, hyphens, and underscores only",
  name: "Name",
  category: "Category",
  categories: {
    Audio: "Audio",
    "Phone Accessories": "Phone accessories",
    "Home Appliances": "Home appliances",
    Skincare: "Skincare",
  },
  price: "Price (EGP)",
  stock: "Stock",
  rawFeatures: "Specifications — one per line",
  featuresExample: "Bluetooth 5.3\nBuilt-in microphone\n30-hour battery",
  image: "JPEG, PNG, or WebP image (maximum 10 MB)",
  analyze: "Analyze product",
  reviewTitle: "2. Review extracted facts",
  reviewHint:
    "AI proposes; you are the final source of approval before activation.",
  features: "Features",
  benefits: "Benefits",
  description: "Description",
  activate: "Save and activate",
  contentTitle: "3. Create platform content",
  contentHint:
    "Content uses only approved facts, with a distinct version per platform and programmatic claim checks.",
  generate: "Create content",
  editTitle: "Edit, then approve",
  validationWarnings: "Content checks need attention",
  facebook: "Facebook text",
  instagram: "Instagram text",
  hashtags: "Hashtags",
  save: "Save changes",
  approve: "Explicit approval",
  approvalHint: "Editing approved content automatically clears its approval.",
  unsavedHint: "Save your content changes before approving.",
  publishTitle: "4. Publish",
  approvalStatus: "Content approval status",
  publishHint:
    "Each platform result is shown below after the request. A demo result does not create a live post.",
  publish: "Publish to both platforms",
  demo: "Demo completed — no live post was created",
  success: "Published successfully",
  failure: "Publishing failed",
  providerStatus: "Provider status",
  providerError: "Provider error",
  noErrorDetails: "No further error details were returned.",
  externalId: "External ID",
  openPost: "Open post ↗",
  statuses: {
    draft: "Draft",
    approved: "Approved",
    published: "Published",
    partial: "Partially published",
    failed: "Failed",
  } satisfies Record<MarketingStatus, string>,
};

const arabic: typeof english = {
  steps: ["البيانات والصورة", "مراجعة الحقائق", "المحتوى", "الموافقة والنشر"],
  eyebrow: "رحلة المنتج",
  title: "إضافة منتج ونشره",
  intro: "أربع خطوات: بياناتك، مراجعتك، محتواك، ثم موافقتك الصريحة قبل أي نشر.",
  running: "جارٍ تنفيذ الخطوة…",
  unexpectedError: "حدث خطأ غير متوقع. حاول تنفيذ الخطوة مرة أخرى.",
  requestFailed: "تعذر إكمال الطلب",
  analysisReady: "تم التحليل. راجع الحقائق قبل التفعيل.",
  activated: "تم تفعيل المنتج وحفظه في قاعدة المعرفة.",
  contentReady: "تم إنشاء نسختين مختلفتين. يمكنك تعديلهما.",
  contentSaved: "حُفظ التعديل وأُلغيت أي موافقة سابقة.",
  approved: "تم تسجيل الموافقة باسمك وتوقيتها.",
  publishFinished:
    "انتهت محاولة النشر. راجع نتيجة كل منصة أدناه. إعادة محاولة هذا الطلب لن تنشئ منشورًا مكررًا.",
  confirmPublish: "هل تؤكد النشر على Facebook وInstagram؟",
  dataTitle: "1. بيانات المنتج والصورة",
  dataHint:
    "الذكاء الاصطناعي سيحلل الصورة ويقترح الحقائق المرئية — وأنت من يعتمدها.",
  productId: "معرّف المنتج",
  productIdHint: "حروف وأرقام و- و_ فقط",
  name: "الاسم",
  category: "الفئة",
  categories: {
    Audio: "الصوتيات",
    "Phone Accessories": "إكسسوارات الهواتف",
    "Home Appliances": "الأجهزة المنزلية",
    Skincare: "العناية بالبشرة",
  },
  price: "السعر بالجنيه",
  stock: "المخزون",
  rawFeatures: "المواصفات — سطر لكل خاصية",
  featuresExample: "Bluetooth 5.3\nميكروفون مدمج\nبطارية 30 ساعة",
  image: "صورة JPEG أو PNG أو WebP (حد أقصى 10 ميجابايت)",
  analyze: "تحليل المنتج",
  reviewTitle: "2. راجع الحقائق المستخرجة",
  reviewHint: "الذكاء الاصطناعي يقترح، وأنت مصدر الاعتماد النهائي قبل التفعيل.",
  features: "الخصائص",
  benefits: "الفوائد",
  description: "الوصف",
  activate: "حفظ وتفعيل",
  contentTitle: "3. أنشئ محتوى المنصتين",
  contentHint:
    "سيُبنى المحتوى من الحقائق التي وافقت عليها فقط — نسخة مختلفة لكل منصة، وفحص برمجي للسعر والادعاءات.",
  generate: "إنشاء المحتوى",
  editTitle: "عدّل ثم اعتمد",
  validationWarnings: "فحوصات المحتوى تحتاج إلى مراجعة",
  facebook: "نص Facebook",
  instagram: "نص Instagram",
  hashtags: "الهاشتاجات",
  save: "حفظ التعديل",
  approve: "موافقة صريحة",
  approvalHint: "أي تعديل بعد الموافقة يلغيها تلقائيًا.",
  unsavedHint: "احفظ تعديلات المحتوى قبل الموافقة.",
  publishTitle: "4. النشر",
  approvalStatus: "حالة موافقة المحتوى",
  publishHint:
    "تظهر نتيجة كل منصة أدناه بعد الطلب. النتيجة التجريبية لا تنشئ منشورًا فعليًا.",
  publish: "نشر على المنصتين",
  demo: "اكتملت التجربة — لم يُنشأ منشور فعلي",
  success: "تم النشر بنجاح",
  failure: "فشل النشر",
  providerStatus: "حالة المنصة",
  providerError: "خطأ المنصة",
  noErrorDetails: "لم تُرجع المنصة تفاصيل إضافية عن الخطأ.",
  externalId: "المعرّف الخارجي",
  openPost: "فتح المنشور ↗",
  statuses: {
    draft: "مسودة",
    approved: "معتمد",
    published: "منشور",
    partial: "منشور جزئيًا",
    failed: "فشل",
  },
};

export function newProductCopy(language: "ar" | "en") {
  return language === "ar" ? arabic : english;
}

export type NewProductNotice =
  | "analysisReady"
  | "activated"
  | "contentReady"
  | "contentSaved"
  | "approved"
  | "publishFinished";
