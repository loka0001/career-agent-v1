import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useSearchParams } from "react-router";
import {
  IconFacebook,
  IconInstagram,
  IconLogout,
  IconPlug,
  IconRefresh,
  IconSpark,
  IconWhatsApp,
} from "../../components/icons";
import { Alert, Badge, Button, Card, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type {
  IntegrationStatus,
  ProviderConnection,
  WhatsAppSettings,
  WhatsAppTemplate,
} from "../../lib/types";
import { MetaConnections } from "./MetaConnections";
import { CommerceConnections } from "./CommerceConnections";
import { integrationReadinessPresentation } from "./integrationStatus";
import { WhatsAppEmbeddedSignup } from "./WhatsAppEmbeddedSignup";

type LocalizedCopy = { ar: string; en: string };
type IntegrationSection = "overview" | "store" | "meta" | "whatsapp";

const integrationSections: Array<{
  id: IntegrationSection;
  label: LocalizedCopy;
}> = [
  { id: "overview", label: { ar: "نظرة عامة", en: "Overview" } },
  { id: "store", label: { ar: "المتجر", en: "Store" } },
  { id: "meta", label: { ar: "Meta", en: "Meta" } },
  { id: "whatsapp", label: { ar: "WhatsApp", en: "WhatsApp" } },
];

export function integrationSectionFromSearch(
  searchParams: URLSearchParams,
): IntegrationSection {
  if (searchParams.has("meta_code") || searchParams.has("meta_state")) {
    return "meta";
  }
  if (searchParams.has("shopify_code") || searchParams.has("shopify_state")) {
    return "store";
  }
  const value = searchParams.get("section");
  return integrationSections.some((section) => section.id === value)
    ? (value as IntegrationSection)
    : "overview";
}

const meta: Record<
  string,
  { title: LocalizedCopy; body: LocalizedCopy; icon: ReactNode }
> = {
  ai: {
    title: { ar: "الذكاء الاصطناعي", en: "Artificial intelligence" },
    body: {
      ar: "تحليل المنتجات وصناعة المحتوى وفهم أسئلة العملاء.",
      en: "Analyze products, create content, and understand customer questions.",
    },
    icon: <IconSpark size={19} />,
  },
  image_storage: {
    title: { ar: "تخزين الصور", en: "Image storage" },
    body: {
      ar: "روابط HTTPS عامة لازمة للنشر الحقيقي على Meta.",
      en: "Public HTTPS URLs required for live publishing to Meta.",
    },
    icon: <IconPlug size={19} />,
  },
  facebook: {
    title: { ar: "Facebook", en: "Facebook" },
    body: {
      ar: "نشر المحتوى على صفحتك الاحترافية.",
      en: "Publish content to your professional page.",
    },
    icon: <IconFacebook size={19} />,
  },
  instagram: {
    title: { ar: "Instagram", en: "Instagram" },
    body: {
      ar: "إنشاء المحتوى ونشره على الحساب الاحترافي.",
      en: "Create and publish content to the professional account.",
    },
    icon: <IconInstagram size={19} />,
  },
};

const emptyForm = {
  mode: "demo" as "demo" | "live",
  display_name: "WhatsApp Business",
  phone_number_id: "",
  waba_id: "",
  access_token: "",
  app_secret: "",
  verify_token: "",
  is_active: true,
};

const connectionNames: Record<string, LocalizedCopy> = {
  facebook_page: { ar: "صفحة Facebook", en: "Facebook Page" },
  instagram_business: { ar: "Instagram Business", en: "Instagram Business" },
  whatsapp_business: { ar: "WhatsApp Business", en: "WhatsApp Business" },
  store: { ar: "متجر إلكتروني", en: "Online store" },
  site: { ar: "موقع إلكتروني", en: "Website" },
};

const connectionStatuses: Record<
  ProviderConnection["status"],
  { label: LocalizedCopy; tone: "neutral" | "success" | "warning" | "error" }
> = {
  pending: { label: { ar: "قيد الإعداد", en: "Pending" }, tone: "warning" },
  connected: { label: { ar: "متصل", en: "Connected" }, tone: "success" },
  degraded: {
    label: { ar: "اتصال ضعيف", en: "Connection degraded" },
    tone: "warning",
  },
  expired: { label: { ar: "انتهت الصلاحية", en: "Expired" }, tone: "error" },
  action_required: {
    label: { ar: "يحتاج إجراء", en: "Action required" },
    tone: "error",
  },
  disconnected: {
    label: { ar: "مفصول", en: "Disconnected" },
    tone: "neutral",
  },
};

function errorMessage(reason: unknown, language: "ar" | "en"): string {
  return reason instanceof ApiError
    ? reason.message
    : language === "ar"
      ? "تعذر تنفيذ الطلب"
      : "The request could not be completed.";
}

export function IntegrationsPage() {
  const { language } = useLanguage();
  const [searchParams, setSearchParams] = useSearchParams();
  const section = integrationSectionFromSearch(searchParams);
  const [items, setItems] = useState<IntegrationStatus[]>([]);
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [whatsapp, setWhatsapp] = useState<WhatsAppSettings | null>(null);
  const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [templateForm, setTemplateForm] = useState({
    name: "",
    language: "ar",
    body: "",
    variables: "",
    category: "UTILITY" as "UTILITY" | "MARKETING" | "AUTHENTICATION",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connectionAction, setConnectionAction] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function setSection(nextSection: IntegrationSection) {
    const nextParams = new URLSearchParams(searchParams);
    if (nextSection === "overview") nextParams.delete("section");
    else nextParams.set("section", nextSection);
    setSearchParams(nextParams, { replace: true });
  }

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [
        integrationResponse,
        connectionResponse,
        whatsappResponse,
        templateResponse,
      ] = await Promise.all([
        api.integrations(),
        api.providerConnections(),
        api.whatsappSettings(),
        api.whatsappTemplates(),
      ]);
      setItems(integrationResponse.integrations);
      setConnections(connectionResponse);
      setWhatsapp(whatsappResponse);
      setTemplates(templateResponse);
      setForm((current) => ({
        ...current,
        mode: whatsappResponse.mode,
        display_name: whatsappResponse.display_name,
        is_active: whatsappResponse.is_active,
      }));
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function loadConnections() {
    const [integrationResponse, connectionResponse] = await Promise.all([
      api.integrations(),
      api.providerConnections(),
    ]);
    setItems(integrationResponse.integrations);
    setConnections(connectionResponse);
  }

  async function checkConnection(connection: ProviderConnection) {
    setConnectionAction(connection.id);
    setError("");
    setNotice("");
    try {
      await api.checkProviderConnection(connection.id);
      await loadConnections();
      setNotice(
        language === "ar"
          ? `تم فحص ${connection.display_name} بدون تنفيذ أي عملية نشر.`
          : `${connection.display_name} was checked without publishing anything.`,
      );
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setConnectionAction("");
    }
  }

  async function disconnectConnection(connection: ProviderConnection) {
    const confirmed = window.confirm(
      language === "ar"
        ? `فصل ${connection.display_name} وإيقاف القنوات المرتبطة به؟`
        : `Disconnect ${connection.display_name} and stop its linked channels?`,
    );
    if (!confirmed) return;
    setConnectionAction(connection.id);
    setError("");
    setNotice("");
    try {
      await api.disconnectProviderConnection(connection.id);
      await loadConnections();
      setNotice(
        language === "ar"
          ? `تم فصل ${connection.display_name} ومسح بيانات الاتصال المحلية.`
          : `${connection.display_name} was disconnected and its local connection data was cleared.`,
      );
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setConnectionAction("");
    }
  }

  async function checkMeta() {
    setSaving(true);
    setError("");
    try {
      await api.checkMeta();
      await loadConnections();
      setNotice(
        language === "ar"
          ? "تم فحص اتصال Meta بدون نشر أي محتوى."
          : "The Meta connection was checked without publishing any content.",
      );
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setSaving(false);
    }
  }

  async function saveWhatsApp(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await api.saveWhatsAppSettings(form);
      setWhatsapp(response);
      await loadConnections();
      setForm((current) => ({
        ...current,
        access_token: "",
        app_secret: "",
        verify_token: "",
      }));
      setNotice(
        language === "ar"
          ? "تم حفظ إعدادات WhatsApp وتشفير بيانات الاتصال."
          : "WhatsApp settings were saved and credentials were encrypted.",
      );
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setSaving(false);
    }
  }

  async function checkWhatsApp() {
    setSaving(true);
    setError("");
    try {
      const response = await api.checkWhatsApp();
      if (!response.success) {
        setError(
          language === "ar"
            ? `فشل الاتصال: ${response.error_code ?? "unknown"}`
            : `Connection failed: ${response.error_code ?? "unknown"}`,
        );
      } else {
        setNotice(
          language === "ar"
            ? "الاتصال سليم، ولم يتم إرسال أي رسالة."
            : "The connection is healthy. No message was sent.",
        );
      }
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setSaving(false);
    }
  }

  async function addTemplate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const created = await api.createWhatsAppTemplate({
        name: templateForm.name,
        language: templateForm.language,
        body: templateForm.body,
        variables: templateForm.variables
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        category: templateForm.category,
      });
      setTemplates((current) => [created, ...current]);
      setTemplateForm({
        name: "",
        language: "ar",
        body: "",
        variables: "",
        category: "UTILITY",
      });
      setNotice(language === "ar" ? "تمت إضافة القالب." : "Template added.");
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setSaving(false);
    }
  }

  async function syncTemplates() {
    setSaving(true);
    setError("");
    try {
      setTemplates(await api.syncWhatsAppTemplates());
      setNotice(
        language === "ar"
          ? "تمت مزامنة حالات القوالب وأسباب الرفض من Meta."
          : "Template statuses and rejection reasons were synced from Meta.",
      );
    } catch (reason) {
      setError(errorMessage(reason, language));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            <IconPlug size={14} />{" "}
            {language === "ar" ? "اتصالات القنوات" : "Channel connections"}
          </span>
          <h1>{language === "ar" ? "التكاملات" : "Integrations"}</h1>
          <p>
            {language === "ar"
              ? "اربط قنوات البيع مع إبقاء بيانات الاتصال مشفرة وغير ظاهرة للفريق."
              : "Connect sales channels while keeping credentials encrypted and hidden from the team."}
          </p>
        </div>
        {section === "meta" ? (
          <Button variant="secondary" onClick={checkMeta} disabled={saving}>
            {language === "ar" ? "فحص اتصال Meta" : "Check Meta connection"}
          </Button>
        ) : (
          <Button
            variant="secondary"
            onClick={() => void load()}
            disabled={loading}
          >
            <IconRefresh size={16} />
            {language === "ar" ? "تحديث الحالات" : "Refresh statuses"}
          </Button>
        )}
      </div>

      <nav
        className="segmented-control integration-sections"
        aria-label={
          language === "ar" ? "أقسام التكاملات" : "Integration sections"
        }
      >
        {integrationSections.map((option) => (
          <button
            key={option.id}
            type="button"
            className={section === option.id ? "active" : ""}
            aria-current={section === option.id ? "page" : undefined}
            onClick={() => setSection(option.id)}
          >
            {option.label[language]}
          </button>
        ))}
      </nav>

      {loading && (
        <Spinner
          label={
            language === "ar"
              ? "جارٍ تحميل التكاملات…"
              : "Loading integrations…"
          }
        />
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {!loading && (
        <>
          {section === "meta" && (
            <MetaConnections
              onConnectionsChanged={() => void loadConnections()}
            />
          )}
          {section === "store" && (
            <CommerceConnections
              connections={connections}
              onChanged={() => void loadConnections()}
            />
          )}
          {section === "overview" && (
            <>
              <section
                className="provider-connections"
                aria-labelledby="provider-connections-title"
              >
                <div className="panel-head">
                  <div>
                    <h2 id="provider-connections-title">
                      {language === "ar"
                        ? "الحسابات المتصلة"
                        : "Connected accounts"}
                    </h2>
                    <p>
                      {language === "ar"
                        ? "حالة الاتصالات الخاصة بهذا المتجر."
                        : "Connection status for this store."}
                    </p>
                  </div>
                  <Badge>{connections.length}</Badge>
                </div>
                <div className="connection-list">
                  {connections.map((connection) => {
                    const status = connectionStatuses[connection.status];
                    const isWorking = connectionAction === connection.id;
                    const isDisconnected = connection.status === "disconnected";
                    return (
                      <div className="connection-row" key={connection.id}>
                        <span className="stat-icon">
                          {connection.connection_type ===
                          "instagram_business" ? (
                            <IconInstagram size={19} />
                          ) : connection.connection_type ===
                            "whatsapp_business" ? (
                            <IconWhatsApp size={19} />
                          ) : (
                            <IconFacebook size={19} />
                          )}
                        </span>
                        <div className="connection-main">
                          <div>
                            <b>{connection.display_name}</b>
                            <small>
                              {connectionNames[connection.connection_type]?.[
                                language
                              ] ?? connection.connection_type}
                              {" · "}
                              {connection.mode === "demo" ? "Demo" : "Live"}
                            </small>
                          </div>
                          <div className="connection-capabilities">
                            {connection.capabilities.map((capability) => (
                              <Badge key={capability}>{capability}</Badge>
                            ))}
                          </div>
                        </div>
                        <Badge tone={status.tone}>
                          {status.label[language]}
                        </Badge>
                        <div className="connection-actions">
                          <Button
                            variant="secondary"
                            title={
                              language === "ar"
                                ? "فحص الاتصال"
                                : "Check connection"
                            }
                            disabled={isWorking || isDisconnected}
                            onClick={() => checkConnection(connection)}
                          >
                            <IconRefresh size={16} />{" "}
                            {language === "ar" ? "فحص" : "Check"}
                          </Button>
                          <Button
                            variant="danger"
                            title={
                              language === "ar"
                                ? "فصل الحساب"
                                : "Disconnect account"
                            }
                            disabled={isWorking || isDisconnected}
                            onClick={() => disconnectConnection(connection)}
                          >
                            <IconLogout size={16} />{" "}
                            {language === "ar" ? "فصل" : "Disconnect"}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                  {connections.length === 0 && (
                    <p className="muted-copy">
                      {language === "ar"
                        ? "لا توجد حسابات متصلة بهذا المتجر."
                        : "No accounts are connected to this store."}
                    </p>
                  )}
                </div>
              </section>
              <div className="integration-grid">
                {items.map((item) => {
                  const info = meta[item.name] ?? {
                    title: { ar: item.name, en: item.name },
                    body: { ar: "", en: "" },
                    icon: <IconPlug size={19} />,
                  };
                  const readiness = integrationReadinessPresentation(
                    item.configured,
                    item.mode,
                    language,
                  );
                  return (
                    <Card key={item.name} className="integration-card" hover>
                      <div className="row-between">
                        <span className="stat-icon">{info.icon}</span>
                        <Badge tone={readiness.tone}>{readiness.label}</Badge>
                      </div>
                      <div>
                        <h3>{info.title[language]}</h3>
                        <p>{info.body[language]}</p>
                      </div>
                      <dl>
                        <div>
                          <dt>{language === "ar" ? "الوضع" : "Mode"}</dt>
                          <dd>{item.mode}</dd>
                        </div>
                        <div>
                          <dt>
                            {language === "ar" ? "المعرّف" : "Identifier"}
                          </dt>
                          <dd>{item.masked_identifier ?? "—"}</dd>
                        </div>
                      </dl>
                    </Card>
                  );
                })}
              </div>
            </>
          )}

          {section === "whatsapp" && (
            <div className="integration-settings-layout">
              <Card className="settings-panel">
                <div className="panel-head">
                  <div>
                    <span className="stat-icon">
                      <IconWhatsApp size={20} />
                    </span>
                    <h2>WhatsApp Business</h2>
                  </div>
                  <Badge tone={whatsapp?.configured ? "success" : "warning"}>
                    {whatsapp?.configured
                      ? language === "ar"
                        ? "جاهز"
                        : "Ready"
                      : language === "ar"
                        ? "يحتاج إعداد"
                        : "Setup required"}
                  </Badge>
                </div>

                <WhatsAppEmbeddedSignup
                  available={Boolean(whatsapp?.embedded_signup_available)}
                  onConnected={() => void load()}
                />

                <details className="advanced-settings">
                  <summary>
                    {language === "ar"
                      ? "إعداد يدوي متقدم"
                      : "Advanced manual setup"}
                  </summary>
                  <form onSubmit={saveWhatsApp} className="form-grid">
                    <label>
                      {language === "ar" ? "وضع التشغيل" : "Operating mode"}
                      <select
                        value={form.mode}
                        onChange={(event) =>
                          setForm({
                            ...form,
                            mode: event.target.value as "demo" | "live",
                          })
                        }
                      >
                        {whatsapp?.demo_available && (
                          <option value="demo">
                            {language === "ar"
                              ? "Demo بدون اتصال خارجي"
                              : "Demo without external connection"}
                          </option>
                        )}
                        <option value="live">
                          {language === "ar"
                            ? "Live عبر WhatsApp Cloud API"
                            : "Live through WhatsApp Cloud API"}
                        </option>
                      </select>
                    </label>
                    <label>
                      {language === "ar" ? "اسم القناة" : "Channel name"}
                      <input
                        value={form.display_name}
                        onChange={(event) =>
                          setForm({ ...form, display_name: event.target.value })
                        }
                        required
                      />
                    </label>
                    <label>
                      Phone Number ID
                      <input
                        value={form.phone_number_id}
                        placeholder={
                          whatsapp?.masked_phone_number_id ??
                          (language === "ar" ? "من Meta" : "From Meta")
                        }
                        onChange={(event) =>
                          setForm({
                            ...form,
                            phone_number_id: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      WABA ID
                      <input
                        value={form.waba_id}
                        placeholder={
                          whatsapp?.masked_waba_id ?? "Business Account ID"
                        }
                        onChange={(event) =>
                          setForm({ ...form, waba_id: event.target.value })
                        }
                      />
                    </label>
                    <label className="full">
                      Access Token
                      <input
                        type="password"
                        value={form.access_token}
                        autoComplete="off"
                        placeholder={
                          language === "ar"
                            ? "اتركه فارغًا للاحتفاظ بالقيمة الحالية"
                            : "Leave blank to keep the current value"
                        }
                        onChange={(event) =>
                          setForm({ ...form, access_token: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      App Secret
                      <input
                        type="password"
                        value={form.app_secret}
                        autoComplete="off"
                        onChange={(event) =>
                          setForm({ ...form, app_secret: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      Verify Token
                      <input
                        type="password"
                        value={form.verify_token}
                        autoComplete="off"
                        onChange={(event) =>
                          setForm({ ...form, verify_token: event.target.value })
                        }
                      />
                    </label>
                    <label className="toggle-row full">
                      <input
                        type="checkbox"
                        checked={form.is_active}
                        onChange={(event) =>
                          setForm({ ...form, is_active: event.target.checked })
                        }
                      />
                      {language === "ar" ? "القناة مفعلة" : "Channel active"}
                    </label>
                    <div className="actions full">
                      <Button type="submit" disabled={saving}>
                        {language === "ar" ? "حفظ الإعدادات" : "Save settings"}
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={checkWhatsApp}
                        disabled={saving || !whatsapp?.configured}
                      >
                        {language === "ar"
                          ? "اختبار الاتصال"
                          : "Test connection"}
                      </Button>
                    </div>
                  </form>
                </details>

                {whatsapp?.webhook_path && (
                  <div className="webhook-box">
                    <span>Webhook URL</span>
                    <code>{`${window.location.origin}${whatsapp.webhook_path}`}</code>
                  </div>
                )}
              </Card>

              <Card className="settings-panel">
                <div className="panel-head">
                  <div>
                    <h2>
                      {language === "ar"
                        ? "قوالب المتابعة"
                        : "Follow-up templates"}
                    </h2>
                    <p>
                      {language === "ar"
                        ? "القالب المعتمد مطلوب بعد إغلاق نافذة خدمة العميل ذات الـ24 ساعة."
                        : "An approved template is required after the 24-hour customer-service window closes."}
                    </p>
                  </div>
                  <div className="actions">
                    <Badge>{templates.length}</Badge>
                    <Button
                      variant="secondary"
                      title={
                        language === "ar" ? "مزامنة القوالب" : "Sync templates"
                      }
                      disabled={saving || !whatsapp?.configured}
                      onClick={() => void syncTemplates()}
                    >
                      <IconRefresh size={16} />
                    </Button>
                  </div>
                </div>
                <form onSubmit={addTemplate}>
                  <div className="form-grid">
                    <label>
                      {language === "ar" ? "اسم القالب" : "Template name"}
                      <input
                        value={templateForm.name}
                        placeholder="follow_up"
                        pattern="[a-z0-9_]+"
                        onChange={(event) =>
                          setTemplateForm({
                            ...templateForm,
                            name: event.target.value,
                          })
                        }
                        required
                      />
                    </label>
                    <label>
                      {language === "ar" ? "اللغة" : "Language"}
                      <input
                        value={templateForm.language}
                        onChange={(event) =>
                          setTemplateForm({
                            ...templateForm,
                            language: event.target.value,
                          })
                        }
                        required
                      />
                    </label>
                    <label>
                      {language === "ar" ? "الفئة" : "Category"}
                      <select
                        value={templateForm.category}
                        onChange={(event) =>
                          setTemplateForm({
                            ...templateForm,
                            category: event.target
                              .value as typeof templateForm.category,
                          })
                        }
                      >
                        <option value="UTILITY">Utility</option>
                        <option value="MARKETING">Marketing</option>
                        <option value="AUTHENTICATION">Authentication</option>
                      </select>
                    </label>
                    <label className="full">
                      {language === "ar" ? "نص القالب" : "Template body"}
                      <textarea
                        value={templateForm.body}
                        placeholder={
                          language === "ar"
                            ? "أهلًا {{name}}، هل ما زلت مهتمًا؟"
                            : "Hi {{name}}, are you still interested?"
                        }
                        onChange={(event) =>
                          setTemplateForm({
                            ...templateForm,
                            body: event.target.value,
                          })
                        }
                        required
                      />
                    </label>
                    <label className="full">
                      {language === "ar" ? "المتغيرات" : "Variables"}
                      <input
                        value={templateForm.variables}
                        placeholder="name, product"
                        onChange={(event) =>
                          setTemplateForm({
                            ...templateForm,
                            variables: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                  <Button type="submit" disabled={saving}>
                    {language === "ar" ? "إضافة القالب" : "Add template"}
                  </Button>
                </form>
                <div className="template-list">
                  {templates.map((template) => (
                    <div className="template-row" key={template.id}>
                      <div>
                        <b>{template.name}</b>
                        <small>{template.body}</small>
                        {template.rejection_reason && (
                          <small className="error-copy">
                            {language === "ar"
                              ? "سبب الرفض:"
                              : "Rejection reason:"}{" "}
                            {template.rejection_reason}
                          </small>
                        )}
                      </div>
                      <Badge
                        tone={
                          template.status === "approved" ? "success" : "warning"
                        }
                      >
                        {template.status}
                      </Badge>
                    </div>
                  ))}
                  {templates.length === 0 && (
                    <p className="muted-copy">
                      {language === "ar"
                        ? "لم تتم إضافة قوالب بعد."
                        : "No templates have been added yet."}
                    </p>
                  )}
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </>
  );
}
