import { Link } from "react-router";
import {
  IconBox,
  IconCheck,
  IconChat,
  IconGlobe,
  IconPlug,
  IconReceipt,
  IconShield,
  IconSpark,
  IconSun,
  IconMoon,
  IconSystem,
  IconTarget,
  IconTrend,
  IconUsers,
  IconWorkflow,
} from "../../components/icons";
import { Badge, Card } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { useTheme } from "../../app/ThemeContext";
import {
  SiInstagram,
  SiMeta,
  SiShopify,
  SiStripe,
  SiWhatsapp,
  SiWoocommerce,
} from "react-icons/si";

const capabilities = [
  {
    icon: IconPlug,
    title: "اربط مصادر تجارتك",
    titleEn: "Connect commerce sources",
    body: "زامن المنتجات والعملاء والطلبات من Shopify أو WooCommerce، واربط قنوات Meta عند جاهزية حساباتك.",
    bodyEn:
      "Sync products, customers, and orders from Shopify or WooCommerce, then connect Meta channels when your accounts are ready.",
  },
  {
    icon: IconChat,
    title: "أدر المحادثات من مكان واحد",
    titleEn: "Operate one inbox",
    body: "تابع الوارد، راجع سياق العميل، واقترح منتجات موجودة فعلًا بأسعار ومخزون مصدرهما قاعدة بيانات متجرك.",
    bodyEn:
      "Follow inbound conversations, inspect customer context, and recommend real products using store-backed prices and stock.",
  },
  {
    icon: IconTarget,
    title: "اكتشف فرص الإيراد",
    titleEn: "Find revenue opportunities",
    body: "حوّل الإشارات القابلة للتنفيذ إلى مهام واضحة، مع سبب الفرصة وإجراء مقترح وسجل للنتيجة.",
    bodyEn:
      "Turn actionable signals into clear tasks with a reason, suggested action, and recorded outcome.",
  },
  {
    icon: IconWorkflow,
    title: "شغّل الأتمتة بضوابط",
    titleEn: "Run controlled automation",
    body: "ابدأ من قوالب تشغيلية، راجع الشروط والإجراءات، وأوقف أي سير عمل أو فعّله دون تغيير خفي.",
    bodyEn:
      "Start from operational templates, inspect conditions and actions, and enable or stop any flow without hidden changes.",
  },
  {
    icon: IconSpark,
    title: "أنشئ محتوى يحتاج موافقتك",
    titleEn: "Create approval-gated content",
    body: "ولّد مسودات مبنية على حقائق المنتج. لا يصبح المحتوى قابلًا للنشر إلا بعد مراجعة وموافقة صريحة.",
    bodyEn:
      "Generate drafts from product facts. Content becomes publishable only after explicit review and approval.",
  },
  {
    icon: IconShield,
    title: "اعمل داخل حدود واضحة",
    titleEn: "Work within clear boundaries",
    body: "عزل كامل بين المتاجر، أدوار وصلاحيات، حماية CSRF، مفاتيح مخفية، وحصص استخدام مطبقة في الخادم.",
    bodyEn:
      "Store isolation, roles, CSRF protection, hidden credentials, and server-enforced usage quotas.",
  },
];

const workflow = [
  {
    label: "اتصل",
    labelEn: "Connect",
    title: "أدخل بيانات المتجر أو اربط منصتك",
    titleEn: "Enter store data or connect a platform",
    body: "ابدأ بمنتج واحد يدويًا، أو جهّز مزامنة Shopify وWooCommerce من صفحة التكاملات.",
    bodyEn:
      "Start with one manual product, or configure Shopify and WooCommerce sync from Integrations.",
  },
  {
    label: "شغّل",
    labelEn: "Operate",
    title: "راقب العمل اليومي من مركز القيادة",
    titleEn: "Run daily work from Command Center",
    body: "الرسائل والطلبات والفرص والأتمتة تظهر في مسارات مستقلة بحالات تحميل وفراغ وخطأ حقيقية.",
    bodyEn:
      "Inbox, orders, opportunities, and automations use dedicated routes with real loading, empty, and error states.",
  },
  {
    label: "استعد",
    labelEn: "Recover",
    title: "استرجع الإيراد بإجراء قابل للتتبع",
    titleEn: "Recover revenue with a traceable action",
    body: "راجع الفرصة، نفّذ الإجراء المناسب، وسجّل النتيجة بدل الاعتماد على أرقام تسويقية مفترضة.",
    bodyEn:
      "Review the opportunity, take the right action, and record the result instead of relying on invented marketing numbers.",
  },
];

const safeguards = [
  {
    ar: "لا نشر تلقائي قبل موافقة مسجلة",
    en: "No automatic publishing before recorded approval",
  },
  {
    ar: "لا بطاقة بنكية ولا بوابة دفع للوصول الحالي",
    en: "No payment card or checkout for current access",
  },
  {
    ar: "الدفع عند الاستلام هو إعداد تحصيل الطلبات الافتراضي",
    en: "Cash on delivery is the default order collection setting",
  },
  {
    ar: "البيانات التجريبية موسومة ولا تختلط ببيانات الإنتاج",
    en: "Demo data is labelled and isolated from production data",
  },
];

const integrationBrands = [
  { name: "Shopify", icon: SiShopify },
  { name: "WooCommerce", icon: SiWoocommerce },
  { name: "Meta", icon: SiMeta },
  { name: "WhatsApp", icon: SiWhatsapp },
  { name: "Instagram", icon: SiInstagram },
  { name: "Stripe", icon: SiStripe },
];

export function LandingPage() {
  const { language, toggle } = useLanguage();
  const { theme, resolvedTheme, toggleTheme } = useTheme();
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link
          to="/"
          className="brand brand--public"
          aria-label="Commerce Revenue Autopilot"
        >
          <span className="brand-mark">
            <IconSpark size={16} />
          </span>
          <span className="brand-copy">
            <b>Commerce</b>
            <small>Revenue Autopilot</small>
          </span>
        </Link>
        <div className="actions">
          <button
            className="button button--ghost icon-button"
            type="button"
            onClick={toggleTheme}
            aria-label={
              theme === "dark"
                ? "Activate light mode"
                : theme === "light"
                  ? "Follow system theme"
                  : "Activate dark mode"
            }
            title={
              theme === "dark"
                ? "Light mode"
                : theme === "light"
                  ? "System theme"
                  : "Dark mode"
            }
          >
            {theme === "system" ? (
              <IconSystem size={18} />
            ) : resolvedTheme === "dark" ? (
              <IconSun size={18} />
            ) : (
              <IconMoon size={18} />
            )}
          </button>
          <button
            className="button button--ghost"
            type="button"
            onClick={toggle}
            aria-label={
              language === "ar" ? "التبديل إلى الإنجليزية" : "Switch to Arabic"
            }
          >
            <IconGlobe size={16} />
            {language === "ar" ? "EN" : "ع"}
          </button>
          <Link className="button button--ghost landing-signin" to="/login">
            {language === "ar" ? "تسجيل الدخول" : "Sign in"}
          </Link>
          <Link className="button button--primary" to="/signup">
            {language === "ar" ? "أنشئ حسابًا مجانيًا" : "Create free account"}
          </Link>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero__copy">
            <span className="eyebrow">
              <IconTrend size={15} />
              {language === "ar"
                ? "عمليات التجارة والإيراد في مساحة عمل واحدة"
                : "Commerce and revenue operations in one workspace"}
            </span>
            <h1>
              {language === "ar"
                ? "شغّل تجارتك بوضوح،"
                : "Operate commerce clearly,"}
              <span>
                {language === "ar"
                  ? " واستعد فرص الإيراد قبل أن تضيع."
                  : " and recover revenue before it slips away."}
              </span>
            </h1>
            <p className="lead">
              {language === "ar"
                ? "اربط بيانات متجرك، أدر المحادثات والطلبات، راجع فرص الإيراد، وشغّل محتوى وأتمتة تحت سيطرتك. كل إجراء مبني على بيانات حقيقية ومسجل داخل مساحة متجرك."
                : "Connect store data, operate conversations and orders, review revenue opportunities, and run content and automation under your control. Every action is grounded in real data and recorded in your store workspace."}
            </p>
            <div className="hero-ctas">
              <Link className="button button--primary button--lg" to="/signup">
                {language === "ar"
                  ? "ابدأ مجانًا — بلا بطاقة"
                  : "Start free — no card"}
              </Link>
              <a
                className="button button--secondary button--lg"
                href="#workflow"
              >
                {language === "ar" ? "شاهد سير العمل" : "See the workflow"}
              </a>
            </div>
            <ul className="hero-points" aria-label="ضمانات البدء">
              <li>
                <IconCheck size={15} />{" "}
                {language === "ar" ? "وصول كامل حاليًا" : "Full access now"}
              </li>
              <li>
                <IconCheck size={15} />{" "}
                {language === "ar"
                  ? "واجهة عربية واتجاه RTL"
                  : "Arabic RTL and English LTR"}
              </li>
              <li>
                <IconCheck size={15} />{" "}
                {language === "ar"
                  ? "لا نشر دون موافقتك"
                  : "No publishing without approval"}
              </li>
            </ul>
          </div>

          <Card className="workflow-preview" aria-label="خريطة مساحة العمل">
            <div className="workflow-preview__head">
              <div>
                <small>{language === "ar" ? "مساحة العمل" : "Workspace"}</small>
                <h2>
                  {language === "ar"
                    ? "من الإشارة إلى الإجراء"
                    : "From signal to action"}
                </h2>
              </div>
              <span className="access-status">
                <IconCheck size={14} />
                {language === "ar" ? "وصول مجاني" : "Free access"}
              </span>
            </div>
            <div className="workflow-preview__rail" aria-hidden="true">
              <span className="is-active">
                {language === "ar" ? "ربط" : "Connect"}
              </span>
              <i />
              <span>{language === "ar" ? "تشغيل" : "Operate"}</span>
              <i />
              <span>{language === "ar" ? "استرداد" : "Recover"}</span>
            </div>
            <div className="workflow-preview__items">
              <div>
                <span className="preview-icon">
                  <IconBox size={18} />
                </span>
                <p>
                  <b>
                    {language === "ar"
                      ? "المنتجات والعملاء"
                      : "Products & customers"}
                  </b>
                  <small>
                    {language === "ar"
                      ? "مصدر الحقيقة للتوصيات والعمليات"
                      : "Source of truth for recommendations and operations"}
                  </small>
                </p>
                <span className="status-dot status-dot--ready">
                  {language === "ar" ? "جاهز" : "Ready"}
                </span>
              </div>
              <div>
                <span className="preview-icon">
                  <IconReceipt size={18} />
                </span>
                <p>
                  <b>
                    {language === "ar"
                      ? "الطلبات والتحصيل"
                      : "Orders & collection"}
                  </b>
                  <small>
                    {language === "ar"
                      ? "حالات واضحة ودفع عند الاستلام"
                      : "Explicit states and cash on delivery"}
                  </small>
                </p>
                <span className="status-dot status-dot--review">
                  {language === "ar" ? "مراجعة" : "Review"}
                </span>
              </div>
              <div>
                <span className="preview-icon">
                  <IconTarget size={18} />
                </span>
                <p>
                  <b>
                    {language === "ar"
                      ? "فرص الإيراد"
                      : "Revenue opportunities"}
                  </b>
                  <small>
                    {language === "ar"
                      ? "سبب وإجراء ونتيجة قابلة للتتبع"
                      : "Traceable reason, action, and result"}
                  </small>
                </p>
                <span className="status-dot status-dot--action">
                  {language === "ar" ? "إجراء" : "Action"}
                </span>
              </div>
            </div>
            <p className="workflow-preview__note">
              {language === "ar"
                ? "هذه خريطة للقدرات وليست لوحة بأرقام أو نتائج مفترضة."
                : "This is a capability map, not a dashboard of invented numbers or results."}
            </p>
          </Card>
        </section>

        <section className="landing-section" id="workflow">
          <div className="section-head">
            <span className="eyebrow">
              {language === "ar"
                ? "اتصل ← شغّل ← استعد"
                : "Connect → Operate → Recover"}
            </span>
            <h2>
              {language === "ar"
                ? "رحلة تشغيلية واحدة بدل أدوات متفرقة"
                : "One operating journey instead of scattered tools"}
            </h2>
            <p>
              {language === "ar"
                ? "ابدأ من بياناتك، نفّذ العمل في سياقه، ثم قِس النتيجة من السجلات الفعلية داخل النظام."
                : "Start with your data, execute work in context, then measure results from actual system records."}
            </p>
          </div>
          <ol className="workflow-steps">
            {workflow.map((step, index) => (
              <li key={step.label}>
                <span className="step-num">{index + 1}</span>
                <small>{language === "ar" ? step.label : step.labelEn}</small>
                <h3>{language === "ar" ? step.title : step.titleEn}</h3>
                <p>{language === "ar" ? step.body : step.bodyEn}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section">
          <div className="section-head">
            <span className="eyebrow">
              {language === "ar"
                ? "قدرات حقيقية ومتصلة"
                : "Real, connected capabilities"}
            </span>
            <h2>
              {language === "ar"
                ? "كل شاشة تقود إلى عمل فعلي"
                : "Every screen leads to real work"}
            </h2>
            <p>
              {language === "ar"
                ? "لا أزرار شكلية ولا بيانات مبيعات مصطنعة. تعرض الواجهة ما ترسله واجهات API، وتشرح بوضوح متى يحتاج موفر خارجي إلى إعداد."
                : "No decorative buttons or fabricated sales data. The UI renders API truth and explains when an external provider needs configuration."}
            </p>
          </div>
          <div className="capabilities-grid">
            {capabilities.map(
              ({ icon: Icon, title, titleEn, body, bodyEn }) => (
                <Card key={title}>
                  <span className="feature-icon">
                    <Icon size={20} />
                  </span>
                  <h3>{language === "ar" ? title : titleEn}</h3>
                  <p>{language === "ar" ? body : bodyEn}</p>
                </Card>
              ),
            )}
          </div>
        </section>

        <section className="landing-section integrations-showcase">
          <div className="section-head section-head--centered">
            <span className="eyebrow">
              {language === "ar" ? "منظومة متصلة" : "Connected ecosystem"}
            </span>
            <h2>
              {language === "ar"
                ? "أدوات تجارتك تعمل من مساحة واحدة"
                : "Your commerce stack, working from one place"}
            </h2>
            <p>
              {language === "ar"
                ? "اربط المنصات التي تستخدمها فعليًا، وراقب حالة كل اتصال ومزامنة بوضوح."
                : "Connect the platforms you already use and see every connection and sync state clearly."}
            </p>
          </div>
          <div
            className="integration-logo-strip"
            role="list"
            aria-label="Supported integrations"
          >
            {integrationBrands.map(({ name, icon: Logo }) => (
              <div className="integration-logo" key={name} role="listitem">
                <span>
                  <Logo size={22} aria-hidden="true" />
                </span>
                <b>{name}</b>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section trust-section">
          <Card className="trust-panel">
            <div>
              <span className="eyebrow">
                <IconShield size={16} />
                {language === "ar" ? "الثقة مدمجة" : "Trust built in"}
              </span>
              <h2>
                {language === "ar"
                  ? "بياناتك وقراراتك تحت سيطرتك"
                  : "Your data and decisions stay under your control"}
              </h2>
              <p>
                {language === "ar"
                  ? "عزل بين المتاجر، صلاحيات حسب الدور، سجلات تدقيق، وموافقة صريحة قبل أي نشر خارجي."
                  : "Tenant isolation, role-based access, audit logs, and explicit approval before external publishing."}
              </p>
            </div>
            <ul className="trust-facts">
              <li>
                <IconShield size={20} />
                {language === "ar"
                  ? "تشفير أثناء النقل والتخزين"
                  : "Encryption in transit and at rest"}
              </li>
              <li>
                <IconCheck size={20} />
                {language === "ar"
                  ? "إجراءات حساسة قابلة للتتبع"
                  : "Traceable sensitive actions"}
              </li>
              <li>
                <IconUsers size={20} />
                {language === "ar"
                  ? "أدوار وصلاحيات واضحة"
                  : "Clear roles and permissions"}
              </li>
            </ul>
          </Card>
        </section>

        <section className="landing-section pricing-preview">
          <div className="section-head section-head--centered">
            <span className="eyebrow">
              {language === "ar" ? "وصول واضح" : "Clear access"}
            </span>
            <h2>
              {language === "ar"
                ? "ابدأ بكل القدرات المتاحة حاليًا"
                : "Start with every capability available today"}
            </h2>
            <p>
              {language === "ar"
                ? "الوصول الحالي مجاني ودون بطاقة. المستويات التالية معروضة كخارطة طريق وليست عروض بيع نشطة."
                : "Current access is free and cardless. Future tiers are shown as a roadmap, not active sales offers."}
            </p>
          </div>
          <div className="pricing-grid">
            <Card className="pricing-preview-card pricing-preview-card--current">
              <Badge tone="success">
                {language === "ar" ? "متاح الآن" : "Available now"}
              </Badge>
              <h3>{language === "ar" ? "الوصول الكامل" : "Full access"}</h3>
              <strong>{language === "ar" ? "مجاني" : "Free"}</strong>
              <p>
                {language === "ar"
                  ? "كل مسارات التشغيل الحالية دون وسيلة دفع."
                  : "Every current operating workflow without a payment method."}
              </p>
            </Card>
            <Card className="pricing-preview-card">
              <Badge>{language === "ar" ? "خارطة الطريق" : "Roadmap"}</Badge>
              <h3>{language === "ar" ? "النمو" : "Growth"}</h3>
              <strong>{language === "ar" ? "لاحقًا" : "Later"}</strong>
              <p>
                {language === "ar"
                  ? "سعات أعلى وتعاون أوسع عند إطلاق التسعير."
                  : "Higher capacities and broader collaboration when pricing launches."}
              </p>
            </Card>
            <Card className="pricing-preview-card">
              <Badge>{language === "ar" ? "خارطة الطريق" : "Roadmap"}</Badge>
              <h3>{language === "ar" ? "المؤسسات" : "Scale"}</h3>
              <strong>{language === "ar" ? "لاحقًا" : "Later"}</strong>
              <p>
                {language === "ar"
                  ? "حوكمة وعمليات متعددة المتاجر للفرق الكبيرة."
                  : "Multi-store governance and operations for larger teams."}
              </p>
            </Card>
          </div>
          <Link className="pricing-link" to="/signup">
            {language === "ar"
              ? "ابدأ بالوصول المجاني"
              : "Start with free access"}
          </Link>
        </section>

        <section className="landing-section access-section">
          <Card className="access-panel">
            <div>
              <span className="eyebrow">
                {language === "ar" ? "الوصول الحالي" : "Current access"}
              </span>
              <h2>
                {language === "ar"
                  ? "استخدم المنتج الآن مجانًا، دون وسيلة دفع."
                  : "Use the product free now, without a payment method."}
              </h2>
              <p>
                {language === "ar"
                  ? "لا توجد أسعار أو ترقية مخفية في هذه المرحلة. تبقى حصص الاستخدام مطبقة لحماية الخدمة، وتظهر لك داخل صفحة الوصول والاستخدام."
                  : "There is no pricing or hidden upgrade at this stage. Usage quotas remain enforced to protect the service and are visible on Access & usage."}
              </p>
              <Link className="button button--primary" to="/signup">
                {language === "ar"
                  ? "أنشئ مساحة متجرك"
                  : "Create your store workspace"}
              </Link>
            </div>
            <ul className="safeguard-list">
              {safeguards.map((item) => (
                <li key={item.ar}>
                  <IconCheck size={16} />
                  {item[language]}
                </li>
              ))}
            </ul>
          </Card>
        </section>
      </main>

      <footer className="landing-footer">
        <div>
          <b>Commerce Revenue Autopilot</b>
          <span>
            {language === "ar"
              ? "بيانات متجرك هي مصدر الحقيقة، وأنت صاحب القرار."
              : "Your store data is the source of truth, and you make the decisions."}
          </span>
        </div>
        <nav aria-label={language === "ar" ? "روابط قانونية" : "Legal links"}>
          <Link to="/terms">{language === "ar" ? "الشروط" : "Terms"}</Link>
          <Link to="/app/privacy">
            {language === "ar" ? "الخصوصية" : "Privacy"}
          </Link>
          <Link to="/login">
            {language === "ar" ? "تسجيل الدخول" : "Sign in"}
          </Link>
        </nav>
      </footer>
    </div>
  );
}
