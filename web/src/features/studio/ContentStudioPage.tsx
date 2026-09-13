import { motion } from "framer-motion";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { useAuth } from "../../app/AuthContext";
import {
  IconCalendar,
  IconFacebook,
  IconInstagram,
  IconSpark,
} from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
} from "../../components/operations";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
} from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { profileCopy } from "../profileCopy";
import type {
  BrandProfile,
  Campaign,
  ContentItem,
  Platform,
  ProductRecord,
} from "../../lib/types";
import { contentStatusPresentation } from "./contentStatus";

const formats = [
  "sales_post",
  "educational_post",
  "story_sequence",
  "carousel",
  "reel_script",
  "limited_offer",
  "comparison",
  "faq",
];
type StudioSource = "content" | "products" | "brand";
const arabicFormats: Record<string, string> = {
  sales_post: "منشور بيعي",
  educational_post: "منشور تعليمي",
  story_sequence: "سلسلة قصص",
  carousel: "منشور متعدد الشرائح",
  reel_script: "نص فيديو قصير",
  limited_offer: "عرض محدود",
  comparison: "مقارنة",
  faq: "أسئلة شائعة",
};
function formatLabel(format: string, language: "ar" | "en") {
  return language === "ar"
    ? (arabicFormats[format] ?? format.replaceAll("_", " "))
    : format.replaceAll("_", " ");
}

export function ContentStudioPage() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const canEdit = !!user && ["owner", "admin", "marketer"].includes(user.role);
  const [params, setParams] = useSearchParams();
  const search = params.get("q") ?? "";
  const statusFilter = params.get("status") ?? "all";
  const selectedId = params.get("content");
  const queueView = !selectedId && params.get("view") !== "cards";
  const composerOpen = !selectedId && params.get("compose") === "1";
  const brandCopy = profileCopy(language).brand;
  const [items, setItems] = useState<ContentItem[]>([]);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [form, setForm] = useState({
    product_id: "",
    content_format: "sales_post",
    platform: "instagram" as Platform,
    tone: "",
    scheduled_for: "",
  });
  const [campaignForm, setCampaignForm] = useState({
    name: "",
    goal: "",
    budget: "1000",
    product_ids: [] as string[],
    audience: "",
    offer: "",
  });
  const [editing, setEditing] = useState<Record<number, string>>({});
  const tab =
    params.get("tab") === "brand"
      ? "brand"
      : params.get("tab") === "campaign"
        ? "campaign"
        : "create";
  function setTab(value: "create" | "brand" | "campaign") {
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("content");
      next.delete("compose");
      next.set("tab", value);
      return next;
    });
  }
  function setComposer(open: boolean) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("content");
      next.set("tab", "create");
      if (open) next.set("compose", "1");
      else next.delete("compose");
      return next;
    });
  }
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const [loading, setLoading] = useState(true);
  const actionLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const refreshLock = useRef(false);
  const [failedSources, setFailedSources] = useState<StudioSource[]>([]);
  const [sourceLoading, setSourceLoading] = useState(false);
  const loadSequence = useRef(0);
  const filteredItems = items.filter(
    (item) =>
      (!selectedId || String(item.id) === selectedId) &&
      (selectedId || statusFilter === "all" || item.status === statusFilter) &&
      (selectedId ||
        `${item.title} ${item.caption} ${item.product_id}`
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase())),
  );
  function filter(key: string, value: string) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("content");
        if (!value || value === "all") next.delete(key);
        else next.set(key, value);
        return next;
      },
      { replace: true },
    );
  }
  function reviewLink(id: number) {
    const next = new URLSearchParams(params);
    next.set("content", String(id));
    return `?${next}`;
  }

  async function refreshDelivery() {
    if (working || refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    setError("");
    try {
      setItems(await api.studioContent());
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  }

  async function load(
    sources: StudioSource[] = ["content", "products", "brand"],
  ) {
    const request = ++loadSequence.current;
    setSourceLoading(true);
    try {
      const [contentResult, productsResult, brandResult] =
        await Promise.allSettled([
          sources.includes("content")
            ? api.studioContent()
            : Promise.resolve(null),
          sources.includes("products") ? api.products() : Promise.resolve(null),
          sources.includes("brand") ? api.brand() : Promise.resolve(null),
        ]);
      if (request !== loadSequence.current) return;
      const failures: StudioSource[] = [];
      if (contentResult.status === "fulfilled") {
        if (contentResult.value) setItems(contentResult.value);
      } else failures.push("content");
      if (brandResult.status === "fulfilled") {
        if (brandResult.value) setBrand(brandResult.value);
      } else failures.push("brand");
      if (productsResult.status === "fulfilled" && productsResult.value) {
        const activeProducts = productsResult.value.filter(
          (item) => item.status === "active",
        );
        setProducts(activeProducts);
        setForm((current) => ({
          ...current,
          product_id: activeProducts.some(
            (product) => product.product_id === current.product_id,
          )
            ? current.product_id
            : activeProducts[0]?.product_id || "",
        }));
      } else if (productsResult.status === "rejected")
        failures.push("products");
      setFailedSources((current) => [
        ...current.filter((source) => !sources.includes(source)),
        ...failures,
      ]);
    } finally {
      if (request === loadSequence.current) {
        setLoading(false);
        setSourceLoading(false);
      }
    }
  }

  useEffect(() => {
    void load();
    return () => {
      ++loadSequence.current;
    };
  }, []);

  async function generate(event: FormEvent) {
    event.preventDefault();
    if (!canEdit || refreshLock.current || working) return;
    setWorking(true);
    setError("");
    try {
      await api.generateContent({
        ...form,
        scheduled_for: form.scheduled_for
          ? new Date(form.scheduled_for).toISOString()
          : null,
      });
      setNotice(
        language === "ar"
          ? "تم إنشاء المسودة والتحقق من حقائق المنتج."
          : "Draft created and product facts checked.",
      );
      await load(["content"]);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  async function saveBrand(event: FormEvent) {
    event.preventDefault();
    if (!canEdit || refreshLock.current || working) return;
    if (!brand) return;
    setWorking(true);
    try {
      setBrand(
        await api.saveBrand({
          tone: brand.tone,
          audience: brand.audience,
          guidelines: brand.guidelines,
          primary_color: brand.primary_color,
        }),
      );
      setNotice(brandCopy.saved);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  async function contentAction(
    item: ContentItem,
    action: "save" | "regenerate" | "approve" | "publish",
  ) {
    const dirty =
      editing[item.id] !== undefined && editing[item.id] !== item.caption;
    if (
      !canEdit ||
      actionLock.current ||
      working ||
      refreshing ||
      [
        "published",
        "publishing",
        "publish_retrying",
        "publish_unknown",
      ].includes(item.status)
    )
      return;
    if (dirty && action !== "save") return;
    actionLock.current = true;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      let updated: ContentItem | undefined;
      if (action === "save")
        updated = await api.editContent(item.id, {
          caption: editing[item.id] ?? item.caption,
        });
      if (action === "regenerate")
        updated = await api.regenerateContent(item.id, "caption");
      if (action === "approve") updated = await api.approveContent(item.id);
      if (action === "publish") {
        await api.publishContent(item.id);
        setItems(await api.studioContent());
      }
      if (updated) {
        const savedItem = updated;
        setItems((current) =>
          current.map((entry) => (entry.id === item.id ? savedItem : entry)),
        );
        setEditing((current) => {
          const next = { ...current };
          delete next[item.id];
          return next;
        });
      }
      setNotice(
        language === "ar"
          ? action === "publish"
            ? "تم قبول طلب النشر. حدّث حالة التسليم لمعرفة النتيجة؛ هذا ليس تأكيدًا للنشر."
            : `تم تنفيذ ${action}.`
          : action === "publish"
            ? "Publication request accepted. Refresh delivery status for the worker result; this is not confirmation of publication."
            : `${action} completed.`,
      );
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      actionLock.current = false;
      setWorking(false);
    }
  }

  async function createCampaign(event: FormEvent) {
    event.preventDefault();
    if (!canEdit || refreshLock.current || working) return;
    setWorking(true);
    try {
      const result = await api.generateCampaign(campaignForm);
      setCampaign(result);
      setNotice(
        language === "ar"
          ? "تم إنشاء الحملة وخطة المنشورات."
          : "Campaign and posting plan created.",
      );
      await load(["content"]);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "استوديو المحتوى" : "Content studio"}
        description={
          language === "ar"
            ? "من المنتج إلى منشور معتمد ومجدول، بصوت البراند وحقائق الكتالوج فقط."
            : "From product to approved, scheduled post using only brand voice and catalog facts."
        }
      />
      <div className="segmented-control" role="tablist">
        <button
          className={tab === "create" ? "active" : ""}
          onClick={() => setComposer(true)}
        >
          {language === "ar" ? "إنشاء محتوى" : "Create content"}
        </button>
        <button
          className={tab === "brand" ? "active" : ""}
          onClick={() => setTab("brand")}
        >
          {language === "ar" ? "صوت البراند" : "Brand voice"}
        </button>
        <button
          className={tab === "campaign" ? "active" : ""}
          onClick={() => setTab("campaign")}
        >
          {language === "ar" ? "مولد الحملات" : "Campaign builder"}
        </button>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {failedSources.length > 0 && (
        <Alert tone="error">
          <p>
            {language === "ar"
              ? "تعذر تحميل بعض الأقسام:"
              : "Some sections could not be loaded:"}{" "}
            {failedSources
              .map(
                (source) =>
                  ({
                    content: language === "ar" ? "المحتوى" : "content",
                    products: language === "ar" ? "المنتجات" : "products",
                    brand: language === "ar" ? "العلامة التجارية" : "brand",
                  })[source],
              )
              .join(" · ")}
          </p>
          <Button
            variant="secondary"
            disabled={sourceLoading || working || refreshing}
            onClick={() => void load(failedSources)}
          >
            {language === "ar"
              ? "إعادة تحميل الأقسام المتعذرة"
              : "Retry unavailable sections"}
          </Button>
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ تحميل الاستوديو…" : "Loading studio…"
          }
        />
      ) : (
        <>
          {!canEdit && (
            <Alert>
              {language === "ar"
                ? "صلاحيتك تتيح مراجعة المحتوى فقط."
                : "Your role has read-only access to content."}
            </Alert>
          )}
          {canEdit && !selectedId && tab === "create" && composerOpen && (
            <Card className="studio-composer">
              <div className="row-between">
                <h2>{language === "ar" ? "إنشاء مسودة" : "Create a draft"}</h2>
                <Button variant="ghost" onClick={() => setComposer(false)}>
                  {language === "ar" ? "إغلاق" : "Close"}
                </Button>
              </div>
              {products.length === 0 ? (
                <Alert tone="warning">
                  {language === "ar"
                    ? "فعّل منتجًا واحدًا على الأقل قبل إنشاء محتوى."
                    : "Activate at least one product before creating content."}{" "}
                  <Link to="/app/products">
                    {language === "ar" ? "افتح المنتجات" : "Open products"}
                  </Link>
                </Alert>
              ) : null}
              <form onSubmit={generate} className="form-grid">
                <label>
                  {language === "ar" ? "المنتج" : "Product"}
                  <select
                    value={form.product_id}
                    onChange={(event) =>
                      setForm({ ...form, product_id: event.target.value })
                    }
                  >
                    {products.map((product) => (
                      <option
                        key={product.product_id}
                        value={product.product_id}
                      >
                        {product.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {language === "ar" ? "القالب" : "Format"}
                  <select
                    value={form.content_format}
                    onChange={(event) =>
                      setForm({ ...form, content_format: event.target.value })
                    }
                  >
                    {formats.map((format) => (
                      <option key={format} value={format}>
                        {formatLabel(format, language)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {language === "ar" ? "المنصة" : "Platform"}
                  <select
                    value={form.platform}
                    aria-label={language === "ar" ? "المنصة" : "Platform"}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        platform: event.target.value as Platform,
                      })
                    }
                  >
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                  </select>
                </label>
                <label>
                  {language === "ar" ? "النبرة" : "Tone"}
                  <input
                    value={form.tone}
                    placeholder={brand?.tone}
                    onChange={(event) =>
                      setForm({ ...form, tone: event.target.value })
                    }
                  />
                </label>
                <label>
                  {language === "ar" ? "موعد النشر" : "Schedule"}
                  <input
                    type="datetime-local"
                    value={form.scheduled_for}
                    onChange={(event) =>
                      setForm({ ...form, scheduled_for: event.target.value })
                    }
                  />
                </label>
                <div className="actions form-action">
                  <Button type="submit" disabled={working || !form.product_id}>
                    <IconSpark size={17} />{" "}
                    {language === "ar" ? "توليد مسودة" : "Generate draft"}
                  </Button>
                </div>
              </form>
            </Card>
          )}
          {canEdit && !selectedId && tab === "brand" && brand && (
            <Card>
              <form onSubmit={saveBrand} className="form-grid">
                <label>
                  {brandCopy.tone}
                  <input
                    value={brand.tone}
                    onChange={(event) =>
                      setBrand({ ...brand, tone: event.target.value })
                    }
                  />
                </label>
                <label>
                  {brandCopy.primaryColor}
                  <input
                    type="color"
                    value={brand.primary_color}
                    onChange={(event) =>
                      setBrand({ ...brand, primary_color: event.target.value })
                    }
                  />
                </label>
                <label className="full">
                  {brandCopy.audience}
                  <textarea
                    value={brand.audience}
                    onChange={(event) =>
                      setBrand({ ...brand, audience: event.target.value })
                    }
                  />
                </label>
                <label className="full">
                  {brandCopy.guidelines}
                  <textarea
                    value={brand.guidelines}
                    onChange={(event) =>
                      setBrand({ ...brand, guidelines: event.target.value })
                    }
                  />
                </label>
                <Button type="submit" disabled={working}>
                  {brandCopy.save}
                </Button>
              </form>
            </Card>
          )}
          {canEdit && !selectedId && tab === "campaign" && (
            <div className="operations-grid">
              <Card>
                <form onSubmit={createCampaign}>
                  <label>
                    {language === "ar" ? "اسم الحملة" : "Campaign name"}
                    <input
                      required
                      value={campaignForm.name}
                      onChange={(event) =>
                        setCampaignForm({
                          ...campaignForm,
                          name: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    {language === "ar" ? "الهدف" : "Goal"}
                    <input
                      required
                      value={campaignForm.goal}
                      onChange={(event) =>
                        setCampaignForm({
                          ...campaignForm,
                          goal: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    {language === "ar" ? "الميزانية" : "Budget"}
                    <input
                      type="number"
                      min="0"
                      value={campaignForm.budget}
                      onChange={(event) =>
                        setCampaignForm({
                          ...campaignForm,
                          budget: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    {language === "ar" ? "الجمهور" : "Audience"}
                    <textarea
                      value={campaignForm.audience}
                      onChange={(event) =>
                        setCampaignForm({
                          ...campaignForm,
                          audience: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    {language === "ar" ? "العرض" : "Offer"}
                    <textarea
                      value={campaignForm.offer}
                      onChange={(event) =>
                        setCampaignForm({
                          ...campaignForm,
                          offer: event.target.value,
                        })
                      }
                    />
                  </label>
                  <fieldset>
                    <legend>
                      {language === "ar"
                        ? "منتجات الحملة"
                        : "Campaign products"}
                    </legend>
                    {products.map((product) => (
                      <label className="check-row" key={product.product_id}>
                        <input
                          type="checkbox"
                          checked={campaignForm.product_ids.includes(
                            product.product_id,
                          )}
                          onChange={(event) =>
                            setCampaignForm({
                              ...campaignForm,
                              product_ids: event.target.checked
                                ? [
                                    ...campaignForm.product_ids,
                                    product.product_id,
                                  ]
                                : campaignForm.product_ids.filter(
                                    (id) => id !== product.product_id,
                                  ),
                            })
                          }
                        />
                        {product.name}
                      </label>
                    ))}
                  </fieldset>
                  <Button
                    type="submit"
                    disabled={working || campaignForm.product_ids.length === 0}
                  >
                    {language === "ar" ? "بناء الحملة" : "Build campaign"}
                  </Button>
                </form>
              </Card>
              {campaign && (
                <Card>
                  <Badge tone="success">{campaign.status}</Badge>
                  <h2>{campaign.name}</h2>
                  <p>{campaign.concept}</p>
                  <h3>
                    {language === "ar" ? "نص صفحة الهبوط" : "Landing page copy"}
                  </h3>
                  <p>{campaign.landing_copy}</p>
                  <h3>WhatsApp</h3>
                  <blockquote>{campaign.whatsapp_template}</blockquote>
                  <div className="tag-list">
                    {campaign.kpis.map((kpi) => (
                      <Badge key={kpi}>{kpi}</Badge>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}

          <div className="row-between">
            <h2>
              {language === "ar"
                ? "مراجعة المحتوى والتسليم"
                : "Content review & delivery"}
            </h2>
            <div className="actions">
              {canEdit && !selectedId && tab === "create" && !composerOpen && (
                <Button onClick={() => setComposer(true)}>
                  <IconSpark size={17} />{" "}
                  {language === "ar" ? "إنشاء مسودة" : "Create draft"}
                </Button>
              )}
              <Button
                variant="secondary"
                disabled={working || refreshing}
                onClick={() => void refreshDelivery()}
              >
                {language === "ar"
                  ? "تحديث حالة التسليم"
                  : "Refresh delivery status"}
              </Button>
            </div>
          </div>
          <Card>
            {selectedId ? (
              <Button variant="ghost" onClick={() => filter("content", "")}>
                {language === "ar"
                  ? "العودة إلى قائمة المحتوى"
                  : "Back to content list"}
              </Button>
            ) : (
              <div className="form-grid">
                <label>
                  {language === "ar" ? "بحث في المحتوى" : "Search content"}
                  <input
                    type="search"
                    value={search}
                    onChange={(event) => filter("q", event.target.value)}
                  />
                </label>
                <label>
                  {language === "ar" ? "حالة المحتوى" : "Content status"}
                  <select
                    value={statusFilter}
                    onChange={(event) => filter("status", event.target.value)}
                  >
                    <option value="all">
                      {language === "ar" ? "كل الحالات" : "All statuses"}
                    </option>
                    {[
                      "draft",
                      "approved",
                      "scheduled",
                      "publishing",
                      "published",
                      "failed",
                      "publish_retrying",
                      "publish_unknown",
                    ].map((status) => (
                      <option key={status} value={status}>
                        {contentStatusPresentation(status, language).label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}
            <p aria-live="polite">
              {filteredItems.length} / {items.length}{" "}
              {language === "ar" ? "منشور" : "posts"}
            </p>
          </Card>
          {!selectedId && (
            <div
              className="actions"
              aria-label={language === "ar" ? "عرض المحتوى" : "Content view"}
            >
              <Button
                variant={queueView ? "primary" : "ghost"}
                aria-pressed={queueView}
                onClick={() => filter("view", "")}
              >
                {language === "ar" ? "قائمة المراجعة" : "Review queue"}
              </Button>
              <Button
                variant={!queueView ? "primary" : "ghost"}
                aria-pressed={!queueView}
                onClick={() => filter("view", "cards")}
              >
                {language === "ar" ? "محررات المنشورات" : "Post editors"}
              </Button>
            </div>
          )}
          {queueView ? (
            <ul
              className="studio-review-queue"
              aria-label={language === "ar" ? "قائمة المراجعة" : "Review queue"}
            >
              {filteredItems.map((item) => {
                const status = contentStatusPresentation(item.status, language);
                const dirty =
                  editing[item.id] !== undefined &&
                  editing[item.id] !== item.caption;
                return (
                  <li key={item.id}>
                    <div className="studio-queue-copy">
                      <Link to={reviewLink(item.id)}>{item.title}</Link>
                      <p>{editing[item.id] ?? item.caption}</p>
                      <small>
                        {item.platform} ·{" "}
                        {formatLabel(item.content_format, language)} ·{" "}
                        {item.product_id}
                      </small>
                      {item.scheduled_for && (
                        <small>
                          {new Date(item.scheduled_for).toLocaleString(
                            language === "ar" ? "ar-EG" : "en-US",
                          )}
                        </small>
                      )}
                      {dirty && (
                        <small>
                          {language === "ar"
                            ? "تعديلات غير محفوظة"
                            : "Unsaved changes"}
                        </small>
                      )}
                      {item.validation_warnings.length > 0 && (
                        <small>
                          {language === "ar"
                            ? "يتطلب مراجعة التحقق"
                            : "Validation review required"}
                        </small>
                      )}
                      {status.guidance && <small>{status.guidance}</small>}
                    </div>
                    <span data-content-status={item.status}>
                      <Badge tone={status.tone}>{status.label}</Badge>
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="content-grid">
              {filteredItems.map((item, index) => {
                const dirty =
                  editing[item.id] !== undefined &&
                  editing[item.id] !== item.caption;
                const immutable =
                  !canEdit ||
                  [
                    "published",
                    "publishing",
                    "publish_retrying",
                    "publish_unknown",
                  ].includes(item.status);
                const statusPresentation = contentStatusPresentation(
                  item.status,
                  language,
                );
                return (
                  <motion.article
                    className="content-card"
                    key={item.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.03, 0.2) }}
                  >
                    <div className="row-between">
                      <span className="platform-mark">
                        {item.platform === "facebook" ? (
                          <IconFacebook />
                        ) : (
                          <IconInstagram />
                        )}
                      </span>
                      <span data-content-status={item.status}>
                        <Badge tone={statusPresentation.tone}>
                          {statusPresentation.label}
                        </Badge>
                      </span>
                    </div>
                    <div>
                      <small className="overline">
                        {formatLabel(item.content_format, language)}
                      </small>
                      <h3>
                        <Link to={reviewLink(item.id)}>{item.title}</Link>
                      </h3>
                      <p>{item.body}</p>
                    </div>
                    <textarea
                      aria-label={`Caption ${item.id}`}
                      disabled={working || refreshing || immutable}
                      value={editing[item.id] ?? item.caption}
                      onChange={(event) =>
                        setEditing({
                          ...editing,
                          [item.id]: event.target.value,
                        })
                      }
                    />
                    {dirty && (
                      <Alert tone="warning">
                        {language === "ar"
                          ? "احفظ تعديلات النص قبل الاعتماد أو النشر. الحفظ يلغي الموافقة السابقة."
                          : "Save caption changes before approval or publication. Saving clears previous approval."}
                        <Button
                          variant="ghost"
                          disabled={working}
                          onClick={() =>
                            setEditing((current) => {
                              const next = { ...current };
                              delete next[item.id];
                              return next;
                            })
                          }
                        >
                          {language === "ar"
                            ? "تجاهل التعديلات"
                            : "Discard changes"}
                        </Button>
                      </Alert>
                    )}
                    <div className="tag-list">
                      {item.hashtags.map((tag) => (
                        <span key={tag}>#{tag.replace(/^#/, "")}</span>
                      ))}
                    </div>
                    {item.scheduled_for && (
                      <small>
                        <IconCalendar size={14} />{" "}
                        {new Date(item.scheduled_for).toLocaleString(
                          language === "ar" ? "ar-EG" : "en-US",
                        )}
                      </small>
                    )}
                    {item.validation_warnings.length > 0 && (
                      <Alert tone="error">
                        {item.validation_warnings.join(" · ")}
                      </Alert>
                    )}
                    {statusPresentation.guidance && (
                      <Alert
                        tone={
                          statusPresentation.tone === "error"
                            ? "error"
                            : "warning"
                        }
                      >
                        {statusPresentation.guidance}
                      </Alert>
                    )}
                    <div className="actions">
                      <Button
                        variant="secondary"
                        disabled={working || refreshing || immutable || !dirty}
                        onClick={() => contentAction(item, "save")}
                      >
                        {language === "ar" ? "حفظ" : "Save"}
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={working || refreshing || immutable || dirty}
                        onClick={() => contentAction(item, "regenerate")}
                      >
                        {language === "ar"
                          ? "إعادة الكابشن"
                          : "Regenerate caption"}
                      </Button>
                      {item.status === "draft" && (
                        <Button
                          disabled={
                            working ||
                            !canEdit ||
                            refreshing ||
                            dirty ||
                            item.validation_warnings.length > 0
                          }
                          onClick={() => contentAction(item, "approve")}
                        >
                          {language === "ar" ? "اعتماد" : "Approve"}
                        </Button>
                      )}
                      {["approved", "scheduled"].includes(item.status) && (
                        <Button
                          disabled={!canEdit || working || refreshing || dirty}
                          onClick={() => contentAction(item, "publish")}
                        >
                          {language === "ar" ? "نشر" : "Publish"}
                        </Button>
                      )}
                    </div>
                  </motion.article>
                );
              })}
            </div>
          )}
          {items.length > 0 && filteredItems.length === 0 && (
            <Alert>
              {selectedId
                ? language === "ar"
                  ? "هذا المحتوى غير متاح. حدّث القائمة أو ارجع إليها."
                  : "This content is unavailable. Refresh or return to the list."
                : language === "ar"
                  ? "لا توجد نتائج مطابقة."
                  : "No content matches these filters."}
            </Alert>
          )}
          {items.length === 0 && !failedSources.includes("content") ? (
            <EmptyState
              title={language === "ar" ? "لا توجد مسودات بعد" : "No drafts yet"}
              body={
                language === "ar"
                  ? "اختر منتجًا نشطًا وأنشئ مسودة؛ لن تظهر أمثلة أو منشورات مفترضة هنا."
                  : "Choose an active product and generate a draft; no sample posts are invented here."
              }
            />
          ) : null}
        </>
      )}
    </MotionPage>
  );
}
