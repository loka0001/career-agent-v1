import type { ProductStatus } from "../../lib/types";

export const productStatusLabels: Record<
  ProductStatus,
  { ar: string; en: string }
> = {
  draft: { ar: "مسودة", en: "Draft" },
  reviewed: { ar: "تمت المراجعة", en: "Reviewed" },
  active: { ar: "نشط", en: "Active" },
};

const copy = {
  en: {
    back: "Back to products",
    details: "Product details",
    facts: "Product facts",
    name: "Name",
    category: "Category",
    description: "Description",
    features: "Features — one per line",
    benefits: "Customer benefits — one per line",
    price: "Price",
    stock: "Stock",
    commercial: "Pricing & inventory",
    currency: "Currency",
    sku: "SKU",
    save: "Save review",
    saving: "Saving…",
    activate: "Activate product",
    activating: "Activating…",
    discard: "Discard changes",
    discardConfirm: "Discard your unsaved product changes?",
    dirty: "Unsaved changes",
    saved:
      "Review saved. Activate the product when you are ready to use these facts.",
    activated: "Product activated.",
    workflow: "Activation",
    reviewHint:
      "Saving marks this product as Reviewed, including an active product. Activation makes the reviewed facts available to sales recommendations.",
    activationHint:
      "Review and save any changes before activating. Activation does not publish social content.",
    source: "Managed by",
    local: "This store",
    external:
      "Price and inventory are managed by the connected store. Update them there, then sync the connection.",
    readOnly:
      "Your role can view products. A marketer, admin, or owner can edit and activate them.",
    failed: "The product could not be loaded.",
    actionFailed: "The change could not be saved. Your edits are still here.",
    retry: "Retry",
    updated: "Last updated",
    required: "Use up to 30 features and 8 customer benefits.",
    stockHint:
      "For products with multiple active variants, stock changes must be made per variant. A rejected change leaves your edits intact.",
  },
  ar: {
    back: "العودة إلى المنتجات",
    details: "تفاصيل المنتج",
    facts: "حقائق المنتج",
    name: "الاسم",
    category: "الفئة",
    description: "الوصف",
    features: "الخصائص — سطر لكل خاصية",
    benefits: "فوائد العميل — سطر لكل فائدة",
    price: "السعر",
    stock: "المخزون",
    commercial: "السعر والمخزون",
    currency: "العملة",
    sku: "رمز SKU",
    save: "حفظ المراجعة",
    saving: "جارٍ الحفظ…",
    activate: "تفعيل المنتج",
    activating: "جارٍ التفعيل…",
    discard: "تجاهل التعديلات",
    discardConfirm: "هل تريد تجاهل تعديلات المنتج غير المحفوظة؟",
    dirty: "تعديلات غير محفوظة",
    saved:
      "حُفظت المراجعة. فعّل المنتج عندما تكون جاهزًا لاستخدام هذه الحقائق.",
    activated: "تم تفعيل المنتج.",
    workflow: "التفعيل",
    reviewHint:
      "الحفظ يغيّر الحالة إلى تمت المراجعة، حتى للمنتج النشط. التفعيل يتيح الحقائق المراجعة لترشيحات المبيعات.",
    activationHint:
      "راجع التعديلات واحفظها قبل التفعيل. تفعيل المنتج لا ينشر محتوى اجتماعيًا.",
    source: "تتم إدارته بواسطة",
    local: "هذا المتجر",
    external:
      "يدير المتجر المتصل السعر والمخزون. حدّثهما هناك ثم زامن الاتصال.",
    readOnly:
      "صلاحيتك تتيح عرض المنتجات. يمكن للمسوّق أو المسؤول أو المالك التعديل والتفعيل.",
    failed: "تعذر تحميل المنتج.",
    actionFailed: "تعذر حفظ التغيير. ما زالت تعديلاتك محفوظة في النموذج.",
    retry: "إعادة المحاولة",
    updated: "آخر تحديث",
    required: "الحد الأقصى 30 خاصية و8 فوائد للعميل.",
    stockHint:
      "إذا كان للمنتج عدة متغيرات نشطة، يجب تعديل مخزون كل متغير على حدة. لن تفقد تعديلاتك إذا رُفض التغيير.",
  },
};

export const productCopy = (language: "ar" | "en") => copy[language];
