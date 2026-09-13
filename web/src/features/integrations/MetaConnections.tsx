import { useEffect, useState } from "react";
import { IconFacebook, IconInstagram, IconPlug } from "../../components/icons";
import { errorText } from "../../components/operations";
import { Alert, Badge, Button, Card, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import type { MetaAccountOption, MetaChannelStatus } from "../../lib/types";

const channelNames: Record<MetaChannelStatus["channel_type"], string> = {
  messenger: "Messenger DMs",
  instagram_dm: "Instagram DMs",
  facebook_comments: "Facebook Comments",
  instagram_comments: "Instagram Comments",
};

export function MetaConnections({
  onConnectionsChanged,
}: {
  onConnectionsChanged?: () => void;
}) {
  const { language } = useLanguage();
  const [channels, setChannels] = useState<MetaChannelStatus[]>([]);
  const [accounts, setAccounts] = useState<MetaAccountOption[]>([]);
  const [oauthTransactionId, setOauthTransactionId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  async function load() {
    try {
      setChannels(await api.metaChannels());
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const query = new URLSearchParams(window.location.search);
    const code = query.get("meta_code");
    const state = query.get("meta_state");
    if (code && state) {
      setWorking(true);
      api
        .exchangeMetaOAuth(code, state)
        .then((result) => {
          setAccounts(result.accounts);
          setOauthTransactionId(result.transaction_id);
          window.history.replaceState({}, "", window.location.pathname);
        })
        .catch((reason) => setError(errorText(reason, language)))
        .finally(() => setWorking(false));
    }
  }, [language]);

  async function startOAuth() {
    setWorking(true);
    setError("");
    try {
      const result = await api.startMetaOAuth();
      if (result.demo) {
        const exchange = await api.exchangeMetaOAuth("demo", result.state);
        setAccounts(exchange.accounts);
        setOauthTransactionId(exchange.transaction_id);
        setNotice(
          language === "ar"
            ? "تم تجهيز حساب Meta تجريبي بدون أي اتصال خارجي."
            : "A demo Meta account is ready without any external connection.",
        );
      } else {
        window.location.assign(result.authorization_url);
      }
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  async function connect(account: MetaAccountOption) {
    setWorking(true);
    try {
      setChannels(
        await api.connectMetaOAuth(
          oauthTransactionId,
          account.page_id,
          account.instagram_account_id,
        ),
      );
      setAccounts([]);
      setOauthTransactionId("");
      setNotice(
        language === "ar"
          ? "تم ربط الرسائل والتعليقات بالحساب المختار."
          : "Messages and comments are connected to the selected account.",
      );
      onConnectionsChanged?.();
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  async function check(channel: MetaChannelStatus) {
    setWorking(true);
    try {
      const result = await api.checkMetaChannel(channel.channel_id);
      setNotice(
        result.success
          ? language === "ar"
            ? `${channelNames[channel.channel_type]} جاهزة.`
            : `${channelNames[channel.channel_type]} is ready.`
          : language === "ar"
            ? `فشل الفحص: ${result.error_code}`
            : `Connection check failed: ${result.error_code}`,
      );
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="meta-connections">
      <div className="panel-head">
        <div>
          <h2>Facebook & Instagram</h2>
          <p>
            {language === "ar"
              ? "OAuth آمن لاختيار الصفحة، مع توضيح الصلاحيات الناقصة وانتهاء التوكن."
              : "Secure OAuth page selection with missing-permission and token-expiry visibility."}
          </p>
        </div>
        <Button onClick={startOAuth} disabled={working}>
          <IconFacebook size={18} />
          {language === "ar" ? "ربط حساب Meta" : "Connect Meta account"}
        </Button>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading && (
        <Spinner
          label={
            language === "ar"
              ? "جاري تحميل قنوات Meta…"
              : "Loading Meta channels…"
          }
        />
      )}
      {working && (
        <Spinner
          label={
            language === "ar"
              ? "جاري إكمال اتصال Meta…"
              : "Completing Meta connection…"
          }
        />
      )}
      {accounts.map((account) => (
        <Card className="account-option" key={account.page_id}>
          <span className="stat-icon">
            <IconFacebook />
          </span>
          <span className="grow">
            <b>{account.page_name}</b>
            <small>
              {account.instagram_username
                ? `@${account.instagram_username}`
                : language === "ar"
                  ? "بدون Instagram Business"
                  : "No Instagram Business account"}
            </small>
          </span>
          <Button onClick={() => connect(account)}>
            {language === "ar" ? "اختيار وربط" : "Select and connect"}
          </Button>
        </Card>
      ))}
      <div className="integration-grid">
        {channels.map((channel) => (
          <Card key={channel.channel_type} className="meta-channel-card">
            <div className="row-between">
              <span className="stat-icon">
                {channel.channel_type.startsWith("instagram") ? (
                  <IconInstagram />
                ) : (
                  <IconFacebook />
                )}
              </span>
              <Badge tone={channel.configured ? "success" : "warning"}>
                {channel.mode}
              </Badge>
            </div>
            <div>
              <h3>{channelNames[channel.channel_type]}</h3>
              <p>{channel.display_name}</p>
            </div>
            {channel.token_expiring && (
              <Alert tone="warning">
                {language === "ar"
                  ? "التوكن سينتهي قريباً ويحتاج تجديد."
                  : "The token expires soon and must be renewed."}
              </Alert>
            )}
            {channel.missing_permissions.length > 0 && (
              <Alert tone="error">
                {language === "ar" ? "صلاحيات ناقصة" : "Missing permissions"}:{" "}
                {channel.missing_permissions.join(", ")}
              </Alert>
            )}
            <small>
              {channel.masked_account_id ??
                (language === "ar"
                  ? "لم يتم ربط حساب"
                  : "No account connected")}
            </small>
            <Button
              variant="secondary"
              disabled={working || !channel.configured}
              onClick={() => check(channel)}
            >
              <IconPlug size={16} />
              {language === "ar" ? "فحص الاتصال" : "Check connection"}
            </Button>
          </Card>
        ))}
      </div>
    </section>
  );
}
