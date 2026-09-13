import { useEffect, useState, type FormEvent } from "react";
import { IconShield } from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
} from "../../components/operations";
import { Alert, Button, Card, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import type { RetentionPolicy } from "../../lib/types";

export function PrivacyPage() {
  const { language } = useLanguage();
  const [policy, setPolicy] = useState<RetentionPolicy | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);

  useEffect(() => {
    api
      .retentionPolicy()
      .then(setPolicy)
      .catch((reason) => setError(errorText(reason)));
  }, []);

  async function downloadExport() {
    setWorking(true);
    setError("");
    try {
      const data = await api.privacyExport();
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `commerce-data-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice("تم تجهيز تصدير البيانات.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function saveRetention(event: FormEvent) {
    event.preventDefault();
    if (!policy) return;
    setWorking(true);
    setError("");
    try {
      setPolicy(await api.saveRetentionPolicy(policy));
      setNotice("تم حفظ سياسة الاحتفاظ.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function requestDeletion(scope: "account" | "store") {
    if (!password) return;
    const confirmed = window.confirm(
      language === "ar"
        ? scope === "account"
          ? "تأكيد طلب حذف الحساب وكل وصولك؟"
          : "تأكيد طلب حذف المتجر وبياناته؟"
        : scope === "account"
          ? "Request deletion of your account and all access?"
          : "Request deletion of this store and its data?",
    );
    if (!confirmed) return;
    setWorking(true);
    setError("");
    try {
      const result =
        scope === "account"
          ? await api.requestAccountDeletion(password)
          : await api.requestStoreDeletion(password);
      setNotice(`تم تسجيل الطلب ${result.request_id}.`);
      setPassword("");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "الخصوصية والاحتفاظ" : "Privacy & retention"}
        description={
          language === "ar"
            ? "تصدير البيانات وسياسات الاحتفاظ وطلبات الحذف."
            : "Data exports, retention policies, and deletion requests."
        }
        action={
          <Button
            variant="secondary"
            onClick={downloadExport}
            disabled={working}
          >
            <IconShield size={17} />{" "}
            {language === "ar" ? "تصدير البيانات" : "Export data"}
          </Button>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {!policy ? (
        <Spinner
          label={
            language === "ar"
              ? "جارٍ تحميل سياسة الاحتفاظ…"
              : "Loading retention policy…"
          }
        />
      ) : (
        <Card>
          <h2>سياسة الاحتفاظ</h2>
          <form className="form-grid" onSubmit={saveRetention}>
            <label>
              الرسائل بالأيام
              <input
                type="number"
                min={30}
                max={2555}
                value={policy.message_days}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    message_days: Number(event.target.value),
                  })
                }
              />
            </label>
            <label>
              المرفقات بالأيام
              <input
                type="number"
                min={1}
                max={365}
                value={policy.media_days}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    media_days: Number(event.target.value),
                  })
                }
              />
            </label>
            <label>
              أحداث الموقع بالأيام
              <input
                type="number"
                min={30}
                max={2555}
                value={policy.event_days}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    event_days: Number(event.target.value),
                  })
                }
              />
            </label>
            <Button type="submit" disabled={working}>
              حفظ السياسة
            </Button>
          </form>
        </Card>
      )}
      <Card className="danger-zone">
        <h2>طلبات الحذف</h2>
        <label>
          تأكيد كلمة المرور
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="actions">
          <Button
            variant="danger"
            disabled={working || password.length < 8}
            onClick={() => requestDeletion("account")}
          >
            حذف حسابي
          </Button>
          <Button
            variant="danger"
            disabled={working || password.length < 8}
            onClick={() => requestDeletion("store")}
          >
            حذف المتجر
          </Button>
        </div>
      </Card>
      <div className="actions">
        <a href="/api/v1/legal/privacy" target="_blank" rel="noreferrer">
          سياسة الخصوصية
        </a>
        <a href="/api/v1/legal/terms" target="_blank" rel="noreferrer">
          شروط الخدمة
        </a>
      </div>
    </MotionPage>
  );
}
