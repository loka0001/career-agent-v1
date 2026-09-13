import { useEffect, useRef, useState, type FormEvent } from "react";
import { IconPlug, IconRefresh } from "../../components/icons";
import { Alert, Badge, Button, Card } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type { ProviderConnection } from "../../lib/types";

const emptyForm = {
  provider: "shopify" as "shopify" | "woocommerce" | "generic_website",
  display_name: "",
  store_url: "",
  access_token: "",
  consumer_key: "",
  consumer_secret: "",
  webhook_secret: "",
  install_webhooks: true,
};

function errorText(reason: unknown, language: "ar" | "en"): string {
  return reason instanceof ApiError
    ? reason.message
    : language === "ar"
      ? "تعذر تنفيذ الطلب"
      : "The request could not be completed";
}

export function CommerceConnections({
  connections,
  onChanged,
}: {
  connections: ProviderConnection[];
  onChanged: () => void;
}) {
  const { language } = useLanguage();
  const [form, setForm] = useState(emptyForm);
  const [working, setWorking] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const handledShopifyOAuth = useRef(false);
  const commerceConnections = connections.filter((connection) =>
    ["shopify", "woocommerce", "generic_website"].includes(connection.provider),
  );

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const code = query.get("shopify_code");
    const state = query.get("shopify_state");
    const shop = query.get("shopify_shop");
    const hmac = query.get("shopify_hmac");
    const timestamp = query.get("shopify_timestamp");
    const host = query.get("shopify_host");
    if (
      code &&
      state &&
      shop &&
      hmac &&
      timestamp &&
      !handledShopifyOAuth.current
    ) {
      handledShopifyOAuth.current = true;
      setWorking("shopify-oauth");
      api
        .exchangeShopifyOAuth({ code, state, shop, hmac, timestamp, host })
        .then((connection) => {
          window.history.replaceState({}, "", window.location.pathname);
          setNotice(
            language === "ar"
              ? `تم تثبيت Shopify OAuth وربط ${connection.display_name}.`
              : `Shopify OAuth installed and ${connection.display_name} connected.`,
          );
          onChanged();
        })
        .catch((reason) => setError(errorText(reason, language)))
        .finally(() => setWorking(""));
    }
  }, [language, onChanged]);

  async function connect(event: FormEvent) {
    event.preventDefault();
    setWorking("connect");
    setError("");
    setNotice("");
    try {
      const result = await api.connectCommerce(form);
      if (result.status !== "connected") {
        setError(
          language === "ar"
            ? "تم حفظ الاتصال لكن فحص المزوّد لم ينجح."
            : "The connection was saved, but its provider check failed.",
        );
      } else {
        setNotice(
          language === "ar"
            ? `تم ربط ${result.display_name} واجتاز فحص الاتصال.`
            : `${result.display_name} connected and passed its health check.`,
        );
      }
      setForm((current) => ({
        ...emptyForm,
        provider: current.provider,
      }));
      onChanged();
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking("");
    }
  }

  async function startShopifyOAuth() {
    const shop = form.store_url.trim();
    if (!shop) {
      setError(
        language === "ar"
          ? "أدخل نطاق Shopify أو رابط المتجر أولاً."
          : "Enter the Shopify domain or store URL first.",
      );
      return;
    }
    setWorking("shopify-oauth");
    setError("");
    setNotice("");
    try {
      const result = await api.startShopifyOAuth({
        display_name: form.display_name.trim() || "Shopify",
        shop,
        install_webhooks: form.install_webhooks,
      });
      window.location.assign(result.authorization_url);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking("");
    }
  }

  async function sync(connection: ProviderConnection) {
    setWorking(connection.id);
    setError("");
    setNotice("");
    try {
      const result = await api.syncCommerce(connection.id);
      setNotice(
        language === "ar"
          ? `المنتجات: ${result.products_created} جديدة، ${result.products_updated} محدثة. ` +
              `الطلبات: ${result.orders_created} جديدة، ${result.orders_updated} محدثة.`
          : `Products: ${result.products_created} created, ${result.products_updated} updated. ` +
              `Orders: ${result.orders_created} created, ${result.orders_updated} updated.`,
      );
      onChanged();
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking("");
    }
  }

  return (
    <section className="commerce-connections" aria-labelledby="commerce-title">
      <div className="panel-head">
        <div>
          <h2 id="commerce-title">
            <IconPlug size={19} />
            {language === "ar" ? "المتجر والموقع" : "Store and website"}
          </h2>
          <p>
            {language === "ar"
              ? "مزامنة الكتالوج والمخزون والطلبات عبر اتصال خاص بهذا المتجر."
              : "Sync catalog, inventory, and orders through a store-scoped connection."}
          </p>
        </div>
        <Badge>{commerceConnections.length}</Badge>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      <div className="integration-settings-layout">
        <Card className="settings-panel">
          <form className="form-grid" onSubmit={connect}>
            <label>
              {language === "ar" ? "المنصة" : "Platform"}
              <select
                value={form.provider}
                onChange={(event) =>
                  setForm({
                    ...emptyForm,
                    provider: event.target.value as typeof form.provider,
                  })
                }
              >
                <option value="shopify">Shopify</option>
                <option value="woocommerce">WooCommerce</option>
                <option value="generic_website">Generic REST</option>
              </select>
            </label>
            <label>
              {language === "ar" ? "اسم الاتصال" : "Connection name"}
              <input
                required
                value={form.display_name}
                onChange={(event) =>
                  setForm({ ...form, display_name: event.target.value })
                }
              />
            </label>
            <label className="full">
              {language === "ar" ? "رابط المتجر" : "Store URL"}
              <input
                required
                dir="ltr"
                type="url"
                placeholder={
                  form.provider === "shopify"
                    ? "https://merchant.myshopify.com"
                    : "https://store.example.com"
                }
                value={form.store_url}
                onChange={(event) =>
                  setForm({ ...form, store_url: event.target.value })
                }
              />
            </label>
            {form.provider === "shopify" && (
              <div className="full">
                <Alert tone="info">
                  {language === "ar"
                    ? "Shopify OAuth يحفظ التوكن في الخادم ويستخدم توقيع Shopify للتحقق من webhooks."
                    : "Shopify OAuth stores the token on the server and verifies webhooks with Shopify signatures."}
                </Alert>
                <Button
                  className="full"
                  type="button"
                  variant="secondary"
                  disabled={working !== ""}
                  onClick={() => void startShopifyOAuth()}
                >
                  {language === "ar"
                    ? "تثبيت Shopify بـOAuth"
                    : "Install Shopify with OAuth"}
                </Button>
              </div>
            )}
            {form.provider === "woocommerce" ? (
              <>
                <label>
                  Consumer Key
                  <input
                    required
                    dir="ltr"
                    autoComplete="off"
                    value={form.consumer_key}
                    onChange={(event) =>
                      setForm({ ...form, consumer_key: event.target.value })
                    }
                  />
                </label>
                <label>
                  Consumer Secret
                  <input
                    required
                    dir="ltr"
                    type="password"
                    autoComplete="off"
                    value={form.consumer_secret}
                    onChange={(event) =>
                      setForm({ ...form, consumer_secret: event.target.value })
                    }
                  />
                </label>
              </>
            ) : (
              <label className="full">
                Access Token
                <input
                  required
                  dir="ltr"
                  type="password"
                  autoComplete="off"
                  value={form.access_token}
                  onChange={(event) =>
                    setForm({ ...form, access_token: event.target.value })
                  }
                />
              </label>
            )}
            {(form.provider === "shopify" || !form.install_webhooks) && (
              <label className="full">
                Webhook Secret
                <input
                  required={form.provider === "shopify"}
                  dir="ltr"
                  type="password"
                  autoComplete="off"
                  value={form.webhook_secret}
                  onChange={(event) =>
                    setForm({ ...form, webhook_secret: event.target.value })
                  }
                />
              </label>
            )}
            <label className="toggle-row full">
              <input
                type="checkbox"
                checked={form.install_webhooks}
                onChange={(event) =>
                  setForm({ ...form, install_webhooks: event.target.checked })
                }
              />
              {language === "ar"
                ? "تسجيل Webhooks تلقائيًا"
                : "Register webhooks automatically"}
            </label>
            <Button className="full" type="submit" disabled={working !== ""}>
              {language === "ar" ? "ربط وفحص الاتصال" : "Connect and check"}
            </Button>
          </form>
        </Card>
        <Card className="settings-panel">
          <h3>{language === "ar" ? "اتصالات المتجر" : "Store connections"}</h3>
          <div className="key-list">
            {commerceConnections.map((connection) => (
              <div className="key-row" key={connection.id}>
                <span className="grow">
                  <b>{connection.display_name}</b>
                  <small dir="ltr">
                    {connection.provider} · {connection.external_resource_id}
                  </small>
                </span>
                <Badge
                  tone={
                    connection.status === "connected" ? "success" : "warning"
                  }
                >
                  {connection.status}
                </Badge>
                <Button
                  variant="secondary"
                  disabled={
                    working !== "" || connection.status === "disconnected"
                  }
                  onClick={() => void sync(connection)}
                >
                  <IconRefresh size={16} />
                  {language === "ar" ? "مزامنة" : "Sync"}
                </Button>
              </div>
            ))}
            {commerceConnections.length === 0 && (
              <p className="muted-copy">
                {language === "ar"
                  ? "لا يوجد اتصال بعد."
                  : "No connection yet."}
              </p>
            )}
          </div>
        </Card>
      </div>
    </section>
  );
}
