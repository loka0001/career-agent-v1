import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { IconCheck, IconShield, IconWallet } from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
  ProgressBar,
} from "../../components/operations";
import { Alert, Badge, Button, Card, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { formatMoney } from "../../lib/format";
import type { BillingCapabilities, Plan, Subscription } from "../../lib/types";

const labels: Record<string, { ar: string; en: string }> = {
  conversations: { ar: "محادثات شهرية", en: "Monthly conversations" },
  channels: { ar: "قنوات متصلة", en: "Connected channels" },
  team_members: { ar: "أعضاء الفريق", en: "Team members" },
  ai_operations: { ar: "عمليات الذكاء الاصطناعي", en: "AI operations" },
  posts: { ar: "منشورات", en: "Posts" },
  automations: { ar: "عمليات أتمتة", en: "Automations" },
};

export function BillingPage() {
  const { language } = useLanguage();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [capabilities, setCapabilities] = useState<BillingCapabilities | null>(
    null,
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [nextSubscription, nextCapabilities] = await Promise.all([
          api.subscription(),
          api.billingCapabilities(),
        ]);
        if (!active) return;
        setSubscription(nextSubscription);
        setCapabilities(nextCapabilities);
        if (!nextCapabilities.free_access) {
          setPlans(await api.plans());
        }
      } catch (reason) {
        if (active) setError(errorText(reason));
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function changePlan(plan: Plan) {
    setWorking(true);
    setError("");
    try {
      const result = await api.changePlan(plan.key);
      if ("url" in result) {
        window.location.assign(result.url);
        return;
      }
      setSubscription(result);
      setNotice(
        language === "ar"
          ? `تم تفعيل باقة ${plan.name}.`
          : `${plan.name} is now active.`,
      );
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function openPortal() {
    setWorking(true);
    setError("");
    try {
      const result = await api.billingPortal();
      window.location.assign(result.url);
    } catch (reason) {
      setError(errorText(reason));
      setWorking(false);
    }
  }

  if (!subscription || !capabilities) {
    return (
      <MotionPage>
        <PageHeading
          title={language === "ar" ? "الوصول والاستخدام" : "Access & usage"}
          description={
            language === "ar"
              ? "حالة الوصول والحصص الفعلية لمساحة متجرك."
              : "Access status and real quotas for your store workspace."
          }
        />
        {error ? (
          <Alert tone="error">{error}</Alert>
        ) : (
          <Spinner
            label={
              language === "ar" ? "جارٍ تحميل حالة الوصول…" : "Loading access…"
            }
          />
        )}
      </MotionPage>
    );
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "الوصول والاستخدام" : "Access & usage"}
        description={
          language === "ar"
            ? "راجع حالة الوصول والحصص التي تحمي جودة الخدمة."
            : "Review your access status and the quotas protecting service quality."
        }
      />
      {error ? <Alert tone="error">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      {capabilities.free_access ? (
        <Card className="free-access-panel">
          <div className="free-access-panel__summary">
            <span className="free-access-panel__icon">
              <IconCheck size={22} />
            </span>
            <div>
              <Badge tone="success">
                {language === "ar" ? "نشط" : "Active"}
              </Badge>
              <h2>
                {language === "ar"
                  ? "وصول مجاني كامل — بلا بطاقة بنكية"
                  : "Full free access — no payment card"}
              </h2>
              <p>
                {language === "ar"
                  ? "لا يوجد تحصيل اشتراك أو مسار ترقية في المرحلة الحالية. تستطيع استخدام قدرات باقة Growth ضمن الحصص الموضحة أدناه."
                  : "There is no subscription checkout or upgrade path at this stage. Growth capabilities are available within the quotas below."}
              </p>
            </div>
          </div>
          <div className="access-facts">
            <span>
              <IconWallet size={17} />
              {language === "ar"
                ? "لا وسيلة دفع مطلوبة"
                : "No payment method required"}
            </span>
            <span>
              <IconShield size={17} />
              {language === "ar"
                ? "الحصص مطبقة في الخادم"
                : "Server-enforced quotas"}
            </span>
          </div>
        </Card>
      ) : (
        <Alert tone="info">
          {capabilities.checkout_available
            ? language === "ar"
              ? "التحصيل الإلكتروني مفعّل لهذه البيئة."
              : "Subscription checkout is enabled in this environment."
            : language === "ar"
              ? "التحصيل الإلكتروني غير مفعّل. لا يمكن بدء عملية دفع."
              : "Subscription checkout is disabled. No payment can be started."}
        </Alert>
      )}

      <Card className="usage-panel">
        <div className="panel-head">
          <div>
            <small>{language === "ar" ? "مستوى الوصول" : "Access level"}</small>
            <h2>{subscription.plan.name}</h2>
          </div>
          <div className="actions">
            <Badge
              tone={
                ["active", "trialing"].includes(subscription.status)
                  ? "success"
                  : "warning"
              }
            >
              {subscription.status} · {subscription.provider}
            </Badge>
            {!capabilities.free_access && capabilities.portal_available ? (
              <Button
                variant="secondary"
                disabled={working}
                onClick={openPortal}
              >
                <IconWallet size={17} />
                {language === "ar" ? "إدارة الدفع والفواتير" : "Manage billing"}
              </Button>
            ) : null}
          </div>
        </div>
        {subscription.cancel_at_period_end ? (
          <Alert tone="warning">
            {language === "ar"
              ? "سينتهي الاشتراك بنهاية الفترة الحالية."
              : "The subscription ends after the current period."}
          </Alert>
        ) : null}
        <div className="usage-grid">
          {Object.entries(subscription.plan.quotas).map(([metric, limit]) => (
            <ProgressBar
              key={metric}
              label={labels[metric]?.[language] ?? metric}
              value={subscription.usage[metric] ?? 0}
              max={limit}
            />
          ))}
        </div>
      </Card>

      {!capabilities.free_access && plans.length ? (
        <div className="plans-grid">
          {plans.map((plan, index) => {
            const current = subscription.plan.key === plan.key;
            return (
              <motion.article
                className={`plan-card ${current ? "current" : ""}`}
                key={plan.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
              >
                <div className="row-between">
                  <span className="plan-icon">
                    <IconWallet />
                  </span>
                  {current ? (
                    <Badge tone="success">
                      {language === "ar" ? "مستواك الحالي" : "Current"}
                    </Badge>
                  ) : null}
                </div>
                <div>
                  <h2>{plan.name}</h2>
                  <div className="plan-price">
                    {formatMoney(plan.price, language)}
                    <small>{language === "ar" ? "/ شهر" : "/ month"}</small>
                  </div>
                </div>
                <ul className="feature-list">
                  {plan.features.map((feature) => (
                    <li key={feature}>
                      <IconCheck size={16} />
                      {feature.replaceAll("_", " ")}
                    </li>
                  ))}
                </ul>
                {capabilities.checkout_available ? (
                  <Button
                    disabled={current || working}
                    variant={current ? "secondary" : "primary"}
                    onClick={() => changePlan(plan)}
                  >
                    {current
                      ? language === "ar"
                        ? "مفعّل"
                        : "Active"
                      : language === "ar"
                        ? "اختيار المستوى"
                        : "Select plan"}
                  </Button>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      ) : null}
    </MotionPage>
  );
}
