import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import {
  IconChat,
  IconDownload,
  IconTrend,
  IconUsers,
} from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
  ProgressBar,
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
import { formatDateTime, formatMoney } from "../../lib/format";
import type { CustomerIntelligence } from "../../lib/types";

export function CustomersPage() {
  const { language } = useLanguage();
  const [params] = useSearchParams();
  const requestedCustomer = params.get("customer");
  const [items, setItems] = useState<CustomerIntelligence[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [segment, setSegment] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .customers()
      .then((result) => {
        if (!active) return;
        setItems(result);
        setSelectedId(
          requestedCustomer
            ? Number(requestedCustomer)
            : (result[0]?.customer.id ?? null),
        );
        if (
          requestedCustomer &&
          !result.some((item) => item.customer.id === Number(requestedCustomer))
        )
          setError(
            language === "ar"
              ? "العميل المطلوب غير متاح."
              : "The requested customer is unavailable.",
          );
      })
      .catch((reason) => {
        if (active) setError(errorText(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [requestedCustomer, language]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return items.filter(
      (item) =>
        (segment === "all" || item.segments.includes(segment)) &&
        (!needle ||
          [
            item.customer.display_name,
            item.customer.phone,
            item.customer.email,
            ...item.segments,
          ]
            .filter(Boolean)
            .some((value) =>
              String(value).toLocaleLowerCase().includes(needle),
            )),
    );
  }, [items, query, segment]);
  const segments = useMemo(
    () => [...new Set(items.flatMap((item) => item.segments))].sort(),
    [items],
  );
  const selected =
    items.find((item) => item.customer.id === selectedId) ?? null;

  function exportCustomers() {
    const cell = (value: unknown) =>
      `"${String(value ?? "").replaceAll('"', '""')}"`;
    const rows = [
      ["name", "phone", "email", "lead_score", "segments", "revenue"],
      ...filtered.map((item) => [
        item.customer.display_name,
        item.customer.phone,
        item.customer.email,
        item.lead_score,
        item.segments.join(" | "),
        item.total_revenue,
      ]),
    ];
    const url = URL.createObjectURL(
      new Blob([rows.map((row) => row.map(cell).join(",")).join("\n")], {
        type: "text/csv;charset=utf-8",
      }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `customers-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "العملاء" : "Customers"}
        description={
          language === "ar"
            ? "ملف موحد عبر القنوات مع درجة واضحة، RFM، احتمال الشراء ومخاطر الانقطاع."
            : "A cross-channel profile with explainable score, RFM, purchase likelihood, and churn risk."
        }
        action={
          <Button
            variant="secondary"
            onClick={exportCustomers}
            disabled={items.length === 0}
          >
            <IconDownload size={17} />
            {language === "ar" ? "تصدير CSV" : "Export CSV"}
          </Button>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {loading ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ تحليل العملاء…" : "Analyzing customers…"
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          title={language === "ar" ? "لا يوجد عملاء بعد" : "No customers yet"}
          body={
            language === "ar"
              ? "سيظهر العملاء بعد وصول محادثة أو مزامنة مصدر تجارة؛ لا تُنشأ ملفات افتراضية."
              : "Customers appear after a conversation or commerce sync; no profiles are fabricated."
          }
        />
      ) : (
        <div className="customer-layout">
          <Card className="customer-list-panel">
            <label className="search-field">
              <span className="sr-only">
                {language === "ar" ? "بحث" : "Search"}
              </span>
              <input
                type="search"
                value={query}
                placeholder={
                  language === "ar"
                    ? "ابحث بالاسم أو الهاتف أو القطاع"
                    : "Search name, phone, or segment"
                }
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <label className="customer-segment-filter">
              <span className="sr-only">
                {language === "ar" ? "القطاع" : "Segment"}
              </span>
              <select
                value={segment}
                onChange={(event) => setSegment(event.target.value)}
              >
                <option value="all">
                  {language === "ar" ? "كل القطاعات" : "All segments"}
                </option>
                {segments.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <div className="customer-list">
              {filtered.length === 0 ? (
                <p className="empty-inline">
                  {language === "ar"
                    ? "لا توجد نتائج مطابقة."
                    : "No matching customers."}
                </p>
              ) : null}
              {filtered.map((item, index) => (
                <motion.button
                  type="button"
                  key={item.customer.id}
                  className={`customer-list-item ${selectedId === item.customer.id ? "selected" : ""}`}
                  onClick={() => setSelectedId(item.customer.id)}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(index * 0.025, 0.2) }}
                >
                  <span className="avatar">
                    {item.customer.display_name.slice(0, 1)}
                  </span>
                  <span className="grow">
                    <b>{item.customer.display_name}</b>
                    <small>
                      {item.segments.slice(0, 2).join(" · ") || "عميل جديد"}
                    </small>
                  </span>
                  <span className="lead-score">{item.lead_score}</span>
                </motion.button>
              ))}
            </div>
          </Card>

          {selected && (
            <div className="customer-detail">
              <Card>
                <div className="profile-head">
                  <span className="avatar avatar--lg">
                    {selected.customer.display_name.slice(0, 1)}
                  </span>
                  <div className="grow">
                    <h2>{selected.customer.display_name}</h2>
                    <p>
                      {selected.customer.phone ??
                        selected.customer.email ??
                        "بدون بيانات اتصال"}
                    </p>
                  </div>
                  <Badge
                    tone={
                      selected.churn_risk === "high"
                        ? "error"
                        : selected.churn_risk === "medium"
                          ? "warning"
                          : "success"
                    }
                  >
                    Churn: {selected.churn_risk}
                  </Badge>
                </div>
                <div className="profile-metrics">
                  <div>
                    <IconTrend size={17} />
                    <span>
                      قيمة العميل
                      <b>{formatMoney(selected.total_revenue, language)}</b>
                    </span>
                  </div>
                  <div>
                    <IconChat size={17} />
                    <span>
                      طلبات مكتملة<b>{selected.completed_orders}</b>
                    </span>
                  </div>
                  <div>
                    <IconUsers size={17} />
                    <span>
                      متوسط الطلب
                      <b>
                        {formatMoney(selected.average_order_value, language)}
                      </b>
                    </span>
                  </div>
                </div>
                <ProgressBar
                  value={selected.purchase_probability}
                  label="احتمال الشراء"
                />
                <div className="tag-list">
                  {selected.segments.map((segment) => (
                    <Badge key={segment}>{segment}</Badge>
                  ))}
                </div>
              </Card>

              <div className="operations-grid">
                <Card>
                  <h2>لماذا هذه الدرجة؟</h2>
                  <div className="signal-list">
                    {selected.score_signals.map((signal) => (
                      <div className="signal-row" key={signal.name}>
                        <span className="grow">
                          <b>{signal.name}</b>
                          <small>{signal.explanation}</small>
                        </span>
                        <Badge
                          tone={signal.contribution > 0 ? "success" : "warning"}
                        >
                          {signal.contribution > 0 ? "+" : ""}
                          {signal.contribution}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <h2>RFM</h2>
                  <div className="rfm-grid">
                    <div>
                      <span>Recency</span>
                      <b>{selected.rfm.recency_score}/5</b>
                      <small>{selected.rfm.recency_days} يوم</small>
                    </div>
                    <div>
                      <span>Frequency</span>
                      <b>{selected.rfm.frequency_score}/5</b>
                      <small>{selected.rfm.frequency} طلب</small>
                    </div>
                    <div>
                      <span>Monetary</span>
                      <b>{selected.rfm.monetary_score}/5</b>
                      <small>
                        {formatMoney(selected.rfm.monetary, language)}
                      </small>
                    </div>
                  </div>
                </Card>
              </div>

              <Card>
                <h2>الخط الزمني الموحد</h2>
                <div className="timeline">
                  {selected.timeline.slice(0, 12).map((event, index) => (
                    <div
                      className="timeline-item"
                      key={`${event.occurred_at}-${index}`}
                    >
                      <span className="timeline-dot" />
                      <div>
                        <b>{event.title}</b>
                        <p>{event.detail}</p>
                        <small>
                          {formatDateTime(event.occurred_at, language)}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </MotionPage>
  );
}
