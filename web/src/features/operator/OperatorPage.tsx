import { useCallback, useEffect, useState } from "react";
import { IconRefresh, IconShield, IconTarget } from "../../components/icons";
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
  Spinner,
  StatCard,
} from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import type {
  OperatorAlert,
  OperatorJob,
  OperatorOverview,
  OperatorStore,
} from "../../lib/types";

export function OperatorPage() {
  const { language } = useLanguage();
  const [overview, setOverview] = useState<OperatorOverview | null>(null);
  const [alerts, setAlerts] = useState<OperatorAlert[]>([]);
  const [stores, setStores] = useState<OperatorStore[]>([]);
  const [jobs, setJobs] = useState<OperatorJob[]>([]);
  const [query, setQuery] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  const load = useCallback(async (search = "") => {
    setError("");
    try {
      const [nextOverview, nextAlerts, nextStores, nextJobs] =
        await Promise.all([
          api.operatorOverview(),
          api.operatorAlerts(),
          api.operatorStores(search),
          api.operatorJobs(),
        ]);
      setOverview(nextOverview);
      setAlerts(nextAlerts.alerts);
      setStores(nextStores);
      setJobs(nextJobs);
    } catch (cause) {
      setError(errorText(cause));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function replay(id: number) {
    setWorking(true);
    try {
      await api.replayOperatorJob(id);
      await load(query);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setWorking(false);
    }
  }

  async function suspend(store: OperatorStore) {
    if (reason.trim().length < 3) return;
    if (
      !window.confirm(
        language === "ar"
          ? `${store.status === "active" ? "تعليق" : "إعادة تفعيل"} المتجر ${store.name}؟`
          : `${store.status === "active" ? "Suspend" : "Reactivate"} ${store.name}?`,
      )
    )
      return;
    setWorking(true);
    try {
      await api.suspendOperatorStore(
        store.id,
        store.status === "active",
        reason,
      );
      await load(query);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "لوحة التشغيل" : "Operator console"}
        description={
          language === "ar"
            ? "صحة المتاجر والتكاملات والمهام دون عرض أسرار."
            : "Store, integration, and job health without exposing secrets."
        }
        action={
          <Button variant="secondary" onClick={() => load(query)}>
            <IconRefresh size={17} /> {language === "ar" ? "تحديث" : "Refresh"}
          </Button>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {!overview ? (
        <Spinner
          label={
            language === "ar"
              ? "جارٍ تحميل حالة التشغيل…"
              : "Loading operator state…"
          }
        />
      ) : (
        <div className="stats-grid">
          <StatCard
            icon={<IconShield />}
            label="المتاجر"
            value={overview.stores}
          />
          <StatCard
            icon={<IconTarget />}
            label="مهام منتظرة"
            value={overview.queue.queued}
          />
          <StatCard
            icon={<IconTarget />}
            label="مهام فاشلة"
            value={overview.queue.failed}
          />
          <StatCard
            icon={<IconShield />}
            label="تكلفة AI"
            value={`$${overview.ai_cost}`}
          />
        </div>
      )}
      <Card>
        <div className="panel-head">
          <h2>Operational alerts</h2>
          <Badge
            tone={
              alerts.some((item) => item.status === "firing")
                ? "error"
                : "success"
            }
          >
            {alerts.filter((item) => item.status === "firing").length}
          </Badge>
        </div>
        {alerts.length === 0 ? (
          <p className="empty-copy">No alert checks are available.</p>
        ) : (
          <div
            className="data-table"
            role="table"
            aria-label="Operational alerts"
          >
            {alerts.map((item) => (
              <div className="table-row" role="row" key={item.code}>
                <div>
                  <strong>{item.code.replaceAll("_", " ")}</strong>
                  <small>{item.message}</small>
                </div>
                <Badge tone={item.status === "firing" ? "error" : "success"}>
                  {item.status}
                </Badge>
                <Badge
                  tone={item.severity === "critical" ? "error" : "warning"}
                >
                  {item.severity}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card>
        <div className="panel-head">
          <h2>المتاجر</h2>
          <div className="actions">
            <input
              aria-label="سبب الإجراء"
              placeholder="سبب التعليق أو الإعادة"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <input
              aria-label="بحث المتاجر"
              placeholder="بحث بالاسم أو الرابط"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <Button variant="secondary" onClick={() => load(query)}>
              بحث
            </Button>
          </div>
        </div>
        {stores.length === 0 ? (
          <p className="empty-copy">لا توجد نتائج مطابقة.</p>
        ) : (
          <div className="data-table" role="table" aria-label="المتاجر">
            {stores.map((store) => (
              <div className="table-row" role="row" key={store.id}>
                <div>
                  <strong>{store.name}</strong>
                  <small>{store.slug}</small>
                </div>
                <Badge tone={store.status === "active" ? "success" : "warning"}>
                  {store.status}
                </Badge>
                <div>
                  <strong>{store.subscription?.plan ?? "بدون خطة"}</strong>
                  <small>{store.subscription?.status}</small>
                </div>
                <div>
                  <strong>${store.ai_cost}</strong>
                  <small>
                    {store.providers
                      .map((item) => `${item.provider}:${item.status}`)
                      .join(" · ") || "لا تكاملات"}
                  </small>
                </div>
                <Button
                  variant={store.status === "active" ? "danger" : "secondary"}
                  disabled={working || reason.trim().length < 3}
                  onClick={() => suspend(store)}
                >
                  {store.status === "active" ? "تعليق" : "إعادة تفعيل"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card>
        <h2>المهام الفاشلة</h2>
        {jobs.length === 0 ? (
          <p className="empty-copy">لا توجد مهام فاشلة.</p>
        ) : (
          <div className="data-table" role="table" aria-label="المهام الفاشلة">
            {jobs.map((job) => (
              <div className="table-row" role="row" key={job.id}>
                <div>
                  <strong>{job.job_type}</strong>
                  <small>
                    #{job.id} · {job.store_id ?? "system"}
                  </small>
                </div>
                <Badge tone="error">
                  {job.attempts}/{job.max_attempts}
                </Badge>
                <small>{job.last_error ?? "خطأ غير متاح"}</small>
                <Button
                  variant="secondary"
                  disabled={working}
                  onClick={() => replay(job.id)}
                >
                  <IconRefresh size={16} /> إعادة التشغيل
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </MotionPage>
  );
}
