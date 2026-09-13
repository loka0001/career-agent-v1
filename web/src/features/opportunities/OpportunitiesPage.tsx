import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  IconRefresh,
  IconSearch,
  IconTarget,
  IconTrend,
} from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
  Pipeline,
} from "../../components/operations";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
  StatCard,
} from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { formatMoney } from "../../lib/format";
import type { Opportunity, OpportunityDashboard } from "../../lib/types";

type Decision = "approve" | "execute" | "reject" | "won";
type View = "kanban" | "table";

const statuses = [
  { id: "new", ar: "جديدة", en: "New" },
  { id: "awaiting_approval", ar: "مؤهلة", en: "Qualified" },
  { id: "executed", ar: "قيد التنفيذ", en: "In progress" },
  { id: "won", ar: "مكتسبة", en: "Won" },
  { id: "rejected", ar: "مغلقة", en: "Closed" },
] as const;

function OpportunityActions({
  item,
  working,
  language,
  decide,
}: {
  item: Opportunity;
  working: boolean;
  language: "ar" | "en";
  decide: (item: Opportunity, decision: Decision) => void;
}) {
  return (
    <div className="actions opportunity-actions">
      {item.status === "new" ? (
        <Button onClick={() => decide(item, "approve")} disabled={working}>
          {language === "ar" ? "تأهيل" : "Qualify"}
        </Button>
      ) : null}
      {item.status === "awaiting_approval" ? (
        <Button onClick={() => decide(item, "execute")} disabled={working}>
          {language === "ar" ? "تنفيذ" : "Execute"}
        </Button>
      ) : null}
      {item.status === "executed" ? (
        <Button onClick={() => decide(item, "won")} disabled={working}>
          {language === "ar" ? "تسجيل البيع" : "Mark won"}
        </Button>
      ) : null}
      {!["won", "rejected"].includes(item.status) ? (
        <Button
          variant="ghost"
          onClick={() => decide(item, "reject")}
          disabled={working}
        >
          {language === "ar" ? "إغلاق" : "Close"}
        </Button>
      ) : null}
    </div>
  );
}

function OpportunityCard({
  item,
  index,
  language,
  working,
  decide,
}: {
  item: Opportunity;
  index: number;
  language: "ar" | "en";
  working: boolean;
  decide: (item: Opportunity, decision: Decision) => void;
}) {
  return (
    <motion.article
      className="opportunity-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.025, 0.18) }}
    >
      <div className="row-between">
        <Badge
          tone={
            item.status === "won"
              ? "success"
              : item.status === "rejected"
                ? "error"
                : "warning"
          }
        >
          {item.status.replaceAll("_", " ")}
        </Badge>
        <span
          className="confidence-ring"
          style={
            {
              "--confidence": `${item.confidence * 3.6}deg`,
            } as React.CSSProperties
          }
        >
          {item.confidence}%
        </span>
      </div>
      <div>
        <small className="overline">
          {item.opportunity_type.replaceAll("_", " ")}
        </small>
        <h3>{item.reason}</h3>
        <p>{item.suggested_action}</p>
      </div>
      <blockquote>{item.message}</blockquote>
      <div className="opportunity-value">
        <span>{language === "ar" ? "قيمة متوقعة" : "Expected value"}</span>
        <b>{formatMoney(item.expected_revenue, language)}</b>
      </div>
      <OpportunityActions
        item={item}
        working={working}
        language={language}
        decide={decide}
      />
    </motion.article>
  );
}

export function OpportunitiesPage() {
  const { language } = useLanguage();
  const [items, setItems] = useState<Opportunity[]>([]);
  const [dashboard, setDashboard] = useState<OpportunityDashboard | null>(null);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [view, setView] = useState<View>(() =>
    window.matchMedia("(max-width: 767px)").matches ? "table" : "kanban",
  );
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");

  async function load() {
    try {
      const [nextItems, nextDashboard] = await Promise.all([
        api.opportunities(),
        api.opportunityDashboard(),
      ]);
      setItems(nextItems);
      setDashboard(nextDashboard);
    } catch (reason) {
      setError(errorText(reason));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return items.filter((item) => {
      if (status !== "all" && item.status !== status) return false;
      return (
        !needle ||
        `${item.reason} ${item.suggested_action} ${item.opportunity_type}`
          .toLocaleLowerCase()
          .includes(needle)
      );
    });
  }, [items, query, status]);

  async function decide(item: Opportunity, decision: Decision) {
    setWorkingId(item.id);
    setError("");
    try {
      await api.decideOpportunity(
        item.id,
        decision,
        decision === "won" ? item.expected_revenue : "0",
      );
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorkingId(null);
    }
  }

  async function scan() {
    setWorkingId(0);
    try {
      await api.scanOpportunities();
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorkingId(null);
    }
  }

  if (!dashboard && !error) return <Spinner label="جاري تحليل فرص الإيراد…" />;

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "فرص الإيراد" : "Revenue Opportunities"}
        description={
          language === "ar"
            ? "إشارات قابلة للتنفيذ مبنية على سلوك العميل والمخزون والطلبات."
            : "Actionable signals grounded in customer behavior, inventory, and orders."
        }
        action={
          <Button onClick={scan} disabled={workingId !== null}>
            <IconRefresh size={17} />
            {language === "ar" ? "تشغيل الفحص" : "Run scan"}
          </Button>
        }
      />
      {error ? <Alert tone="error">{error}</Alert> : null}
      {dashboard ? (
        <>
          <div className="stats-grid">
            <StatCard
              icon={<IconTrend />}
              label={language === "ar" ? "إيراد محتمل" : "Potential revenue"}
              value={formatMoney(dashboard.potential_revenue, language)}
            />
            <StatCard
              icon={<IconTarget />}
              label={language === "ar" ? "فرص جديدة" : "New opportunities"}
              value={dashboard.new_count}
            />
            <StatCard
              icon={<IconTarget />}
              label={
                language === "ar" ? "بانتظار الموافقة" : "Awaiting approval"
              }
              value={dashboard.awaiting_approval_count}
            />
            <StatCard
              icon={<IconTrend />}
              label={language === "ar" ? "إيراد مستعاد" : "Recovered revenue"}
              value={formatMoney(dashboard.recovered_revenue, language)}
            />
          </div>
          <Card className="pipeline-card">
            <h2>
              {language === "ar"
                ? "خط تحويل الفرصة إلى بيع"
                : "Opportunity conversion pipeline"}
            </h2>
            <Pipeline
              items={Object.entries(dashboard.funnel).map(([label, value]) => ({
                label,
                value,
              }))}
            />
          </Card>
        </>
      ) : null}

      <Card className="opportunity-toolbar">
        <label className="search-field">
          <span className="sr-only">
            {language === "ar" ? "بحث" : "Search"}
          </span>
          <IconSearch size={18} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={
              language === "ar" ? "ابحث في الفرص…" : "Search opportunities…"
            }
          />
        </label>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          aria-label={language === "ar" ? "حالة الفرصة" : "Opportunity status"}
        >
          <option value="all">
            {language === "ar" ? "كل الحالات" : "All statuses"}
          </option>
          {statuses.map((item) => (
            <option key={item.id} value={item.id}>
              {language === "ar" ? item.ar : item.en}
            </option>
          ))}
        </select>
        <div
          className="segmented-control"
          role="group"
          aria-label={language === "ar" ? "طريقة العرض" : "View mode"}
        >
          <button
            type="button"
            className={view === "kanban" ? "active" : ""}
            aria-pressed={view === "kanban"}
            onClick={() => setView("kanban")}
          >
            {language === "ar" ? "لوحة" : "Kanban"}
          </button>
          <button
            type="button"
            className={view === "table" ? "active" : ""}
            aria-pressed={view === "table"}
            onClick={() => setView("table")}
          >
            {language === "ar" ? "جدول" : "Table"}
          </button>
        </div>
      </Card>

      {view === "kanban" ? (
        <div className="opportunity-kanban">
          {statuses.map((column) => {
            const columnItems = visible.filter(
              (item) => item.status === column.id,
            );
            const total = columnItems.reduce(
              (sum, item) => sum + Number(item.expected_revenue),
              0,
            );
            return (
              <section className="opportunity-column" key={column.id}>
                <header>
                  <div>
                    <b>{language === "ar" ? column.ar : column.en}</b>
                    <Badge>{columnItems.length}</Badge>
                  </div>
                  <small>{formatMoney(total, language)}</small>
                </header>
                <div className="opportunity-column__items">
                  {columnItems.map((item, index) => (
                    <OpportunityCard
                      key={item.id}
                      item={item}
                      index={index}
                      language={language}
                      working={workingId === item.id}
                      decide={(target, decision) =>
                        void decide(target, decision)
                      }
                    />
                  ))}
                  {!columnItems.length ? (
                    <p>
                      {language === "ar"
                        ? "اسحب الفرص إلى هنا"
                        : "Move opportunities here"}
                    </p>
                  ) : null}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <Card className="table-wrap opportunity-table">
          <table>
            <thead>
              <tr>
                <th>{language === "ar" ? "الفرصة" : "Opportunity"}</th>
                <th>{language === "ar" ? "القيمة" : "Value"}</th>
                <th>{language === "ar" ? "الثقة" : "Confidence"}</th>
                <th>{language === "ar" ? "الحالة" : "Status"}</th>
                <th>{language === "ar" ? "إجراء" : "Action"}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.reason}</b>
                    <small>{item.suggested_action}</small>
                  </td>
                  <td>{formatMoney(item.expected_revenue, language)}</td>
                  <td>{item.confidence}%</td>
                  <td>
                    <Badge>{item.status.replaceAll("_", " ")}</Badge>
                  </td>
                  <td>
                    <OpportunityActions
                      item={item}
                      working={workingId === item.id}
                      language={language}
                      decide={(target, decision) =>
                        void decide(target, decision)
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {!visible.length ? (
        <EmptyState
          title={
            language === "ar"
              ? "لا توجد فرص مطابقة"
              : "No matching opportunities"
          }
          body={
            language === "ar"
              ? "غيّر البحث أو الفلتر، أو شغّل فحصًا جديدًا."
              : "Change the search or filter, or run a new scan."
          }
          action={
            <Button onClick={scan}>
              {language === "ar" ? "تشغيل الفحص" : "Run scan"}
            </Button>
          }
        />
      ) : null}
    </MotionPage>
  );
}
