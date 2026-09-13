import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { IconRefresh, IconWorkflow } from "../../components/icons";
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
import { formatDateTime } from "../../lib/format";
import type { Automation, AutomationRun } from "../../lib/types";

export function AutomationsPage() {
  const { language } = useLanguage();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [templates, setTemplates] = useState<{ key: string; name: string }[]>(
    [],
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [nextAutomations, nextRuns, nextTemplates] = await Promise.all([
        api.automations(),
        api.automationRuns(),
        api.automationTemplates(),
      ]);
      setAutomations(nextAutomations);
      setRuns(nextRuns);
      setTemplates(nextTemplates);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function install(key: string) {
    setWorking(true);
    try {
      await api.installAutomationTemplate(key);
      setNotice(
        language === "ar"
          ? "تم تثبيت الأتمتة وأصبحت جاهزة للعمل."
          : "Automation installed and ready.",
      );
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function toggle(item: Automation) {
    setWorking(true);
    try {
      await api.setAutomationEnabled(item.id, !item.is_enabled);
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "الأتمتة" : "Automations"}
        description={
          language === "ar"
            ? "محفزات وشروط وإجراءات قابلة للتتبع مع موافقة بشرية عند الحاجة."
            : "Traceable triggers, conditions, and actions with human approval when required."
        }
        action={
          <Button variant="secondary" onClick={load}>
            <IconRefresh size={17} /> {language === "ar" ? "تحديث" : "Refresh"}
          </Button>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ تحميل الأتمتة…" : "Loading automations…"
          }
        />
      ) : (
        <>
          <Card className="template-strip">
            <div>
              <IconWorkflow size={24} />
              <span>
                <b>{language === "ar" ? "قوالب جاهزة" : "Ready templates"}</b>
                <small>
                  {language === "ar"
                    ? "ابدأ بتدفق مجرّب ويمكن تعطيله فوراً."
                    : "Start with an inspectable flow that can be disabled immediately."}
                </small>
              </span>
            </div>
            <div className="actions">
              {templates.map((template) => (
                <Button
                  variant="secondary"
                  disabled={working}
                  key={template.key}
                  onClick={() => install(template.key)}
                >
                  {template.name}
                </Button>
              ))}
            </div>
          </Card>
          {automations.length === 0 ? (
            <EmptyState
              title={
                language === "ar"
                  ? "لا توجد أتمتة مثبتة"
                  : "No installed automations"
              }
              body={
                language === "ar"
                  ? "ثبّت قالبًا أعلاه؛ لن ينشئ النظام تدفقات أو تشغيلات افتراضية."
                  : "Install a template above; the system never invents flows or runs."
              }
            />
          ) : null}
          <div className="automation-grid">
            {automations.map((item, index) => (
              <motion.article
                className="automation-card"
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
              >
                <div className="row-between">
                  <span className="workflow-icon">
                    <IconWorkflow />
                  </span>
                  <label
                    className="switch"
                    title={item.is_enabled ? "تعطيل" : "تفعيل"}
                  >
                    <input
                      type="checkbox"
                      checked={item.is_enabled}
                      disabled={working}
                      onChange={() => toggle(item)}
                    />
                    <span />
                  </label>
                </div>
                <div>
                  <h3>{item.name}</h3>
                  <Badge>{item.trigger_type.replaceAll("_", " ")}</Badge>
                </div>
                <div className="flow-line">
                  <span>{language === "ar" ? "عند" : "When"}</span>
                  <b>{item.trigger_type}</b>
                  <i />
                  <span>{language === "ar" ? "ينفذ" : "Do"}</span>
                  <b>
                    {item.actions
                      .map((action) => action.action_type)
                      .join(", ")}
                  </b>
                </div>
                <div className="automation-meta">
                  <span>
                    {item.conditions.length}{" "}
                    {language === "ar" ? "شروط" : "conditions"}
                  </span>
                  <span>
                    {item.delay_seconds
                      ? `${item.delay_seconds}s ${language === "ar" ? "تأخير" : "delay"}`
                      : language === "ar"
                        ? "فوري"
                        : "Immediate"}
                  </span>
                  <span>
                    {item.approval_required
                      ? language === "ar"
                        ? "بموافقة"
                        : "Approval required"
                      : language === "ar"
                        ? "تلقائي"
                        : "Automatic"}
                  </span>
                </div>
              </motion.article>
            ))}
          </div>
          <Card className="runs-table">
            <div className="panel-head">
              <h2>{language === "ar" ? "سجل التشغيل" : "Run history"}</h2>
              <Badge>{runs.length}</Badge>
            </div>
            <div className="data-table">
              <div className="data-row data-head">
                <span>Run</span>
                <span>Automation</span>
                <span>{language === "ar" ? "الحالة" : "Status"}</span>
                <span>{language === "ar" ? "التوقيت" : "Time"}</span>
              </div>
              {runs.length === 0 ? (
                <p className="empty-inline">
                  {language === "ar"
                    ? "لا توجد تشغيلات مسجلة."
                    : "No recorded runs."}
                </p>
              ) : null}
              {runs.slice(0, 30).map((run) => (
                <div className="data-row" key={run.id}>
                  <b>#{run.id}</b>
                  <span>#{run.automation_id}</span>
                  <Badge
                    tone={
                      run.status === "succeeded"
                        ? "success"
                        : run.status === "failed"
                          ? "error"
                          : "warning"
                    }
                  >
                    {run.status}
                  </Badge>
                  <small>{formatDateTime(run.created_at, language)}</small>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </MotionPage>
  );
}
