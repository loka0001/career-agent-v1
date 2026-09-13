import { useEffect, useRef, useState } from "react";
import { IconRefresh, IconWhatsApp } from "../../components/icons";
import { errorText } from "../../components/operations";
import { Alert, Badge, Button, Card } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import type { WhatsAppPhoneOption } from "../../lib/types";

interface FacebookLoginResponse {
  authResponse?: { code?: string };
  status?: string;
}

interface FacebookSdk {
  init: (options: {
    appId: string;
    cookie: boolean;
    xfbml: boolean;
    version: string;
  }) => void;
  login: (
    callback: (response: FacebookLoginResponse) => void,
    options: Record<string, unknown>,
  ) => void;
}

declare global {
  interface Window {
    FB?: FacebookSdk;
    fbAsyncInit?: () => void;
  }
}

async function loadFacebookSdk(
  appId: string,
  apiVersion: string,
): Promise<FacebookSdk> {
  if (window.FB) {
    window.FB.init({ appId, cookie: true, xfbml: false, version: apiVersion });
    return window.FB;
  }
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(
      () => reject(new Error("Meta SDK timed out")),
      15000,
    );
    window.fbAsyncInit = () => {
      window.clearTimeout(timeout);
      if (!window.FB) {
        reject(new Error("Meta SDK is unavailable"));
        return;
      }
      window.FB.init({
        appId,
        cookie: true,
        xfbml: false,
        version: apiVersion,
      });
      resolve(window.FB);
    };
    const existing = document.getElementById("facebook-jssdk");
    if (existing) return;
    const script = document.createElement("script");
    script.id = "facebook-jssdk";
    script.async = true;
    script.defer = true;
    script.crossOrigin = "anonymous";
    script.src = "https://connect.facebook.net/en_US/sdk.js";
    script.onerror = () => {
      window.clearTimeout(timeout);
      reject(new Error("Meta SDK failed to load"));
    };
    document.head.appendChild(script);
  });
}

export function WhatsAppEmbeddedSignup({
  available,
  onConnected,
}: {
  available: boolean;
  onConnected: () => void;
}) {
  const { language } = useLanguage();
  const [phones, setPhones] = useState<WhatsAppPhoneOption[]>([]);
  const [transactionId, setTransactionId] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const capturedWaba = useRef<string | null>(null);

  useEffect(() => {
    function captureSession(event: MessageEvent) {
      if (
        event.origin !== "https://www.facebook.com" &&
        event.origin !== "https://web.facebook.com"
      )
        return;
      let payload: unknown = event.data;
      if (typeof payload === "string") {
        try {
          payload = JSON.parse(payload);
        } catch {
          return;
        }
      }
      if (!payload || typeof payload !== "object") return;
      const record = payload as {
        type?: string;
        event?: string;
        data?: { waba_id?: string };
      };
      if (record.type === "WA_EMBEDDED_SIGNUP" && record.event === "FINISH") {
        capturedWaba.current = record.data?.waba_id ?? null;
      }
    }
    window.addEventListener("message", captureSession);
    return () => window.removeEventListener("message", captureSession);
  }, []);

  async function start() {
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const setup = await api.startWhatsAppEmbedded();
      const sdk = await loadFacebookSdk(setup.app_id, setup.api_version);
      sdk.login(
        async (response) => {
          const code = response.authResponse?.code;
          if (!code) {
            setWorking(false);
            setError(
              language === "ar"
                ? "لم يكتمل تفويض Meta."
                : "Meta authorization was not completed.",
            );
            return;
          }
          try {
            const exchange = await api.exchangeWhatsAppEmbedded(
              code,
              setup.state,
              capturedWaba.current,
            );
            setPhones(exchange.phones);
            setTransactionId(exchange.transaction_id);
            setNotice(
              language === "ar"
                ? "اختر رقم WhatsApp الذي سيعمل عليه المتجر."
                : "Choose the WhatsApp number this store will use.",
            );
          } catch (reason) {
            setError(errorText(reason, language));
          } finally {
            setWorking(false);
          }
        },
        {
          config_id: setup.config_id,
          response_type: "code",
          override_default_response_type: true,
          extras: {
            setup: setup.solution_id ? { solutionID: setup.solution_id } : {},
            featureType: "",
            sessionInfoVersion: "3",
          },
        },
      );
    } catch (reason) {
      setError(errorText(reason, language));
      setWorking(false);
    }
  }

  async function connect(phone: WhatsAppPhoneOption) {
    setWorking(true);
    setError("");
    try {
      await api.connectWhatsAppEmbedded(
        transactionId,
        phone.phone_number_id,
        phone.waba_id,
        pin || null,
      );
      setPhones([]);
      setTransactionId("");
      setNotice(
        language === "ar"
          ? "تم تسجيل الرقم والاشتراك في Webhooks وفحص بيانات الاتصال."
          : "The number was registered, subscribed to webhooks, and its connection was checked.",
      );
      onConnected();
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="embedded-signup">
      <div className="panel-head">
        <div>
          <h3>
            <IconWhatsApp size={18} />{" "}
            {language === "ar"
              ? "الربط السريع الرسمي"
              : "Official quick connection"}
          </h3>
          <p>
            {language === "ar"
              ? "يفتح Meta Embedded Signup ثم يعرض الأرقام الممنوحة لحسابك فقط."
              : "Open Meta Embedded Signup and show only the phone numbers granted to your account."}
          </p>
        </div>
        <Button onClick={start} disabled={working || !available}>
          <IconWhatsApp size={17} />{" "}
          {language === "ar" ? "ربط WhatsApp" : "Connect WhatsApp"}
        </Button>
      </div>
      {!available && (
        <Alert tone="warning">
          {language === "ar"
            ? "Embedded Signup ينتظر إعداد Meta App في بيئة الإنتاج."
            : "Embedded Signup is waiting for the Meta app to be configured in production."}
        </Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {phones.length > 0 && (
        <label>
          {language === "ar"
            ? "PIN التسجيل المكوّن من 6 أرقام، إن طلبه الرقم"
            : "Six-digit registration PIN, if required for this number"}
          <input
            inputMode="numeric"
            value={pin}
            onChange={(event) =>
              setPin(event.target.value.replace(/\D/g, "").slice(0, 6))
            }
          />
        </label>
      )}
      {phones.map((phone) => (
        <Card className="account-option" key={phone.phone_number_id}>
          <span className="stat-icon">
            <IconWhatsApp size={18} />
          </span>
          <span className="grow">
            <b>{phone.verified_name || phone.display_phone_number}</b>
            <small dir="ltr">{phone.display_phone_number}</small>
          </span>
          <Badge tone={phone.quality_rating === "RED" ? "error" : "success"}>
            {phone.quality_rating ||
              phone.verification_status ||
              (language === "ar" ? "متاح" : "Available")}
          </Badge>
          <Button
            disabled={working || (pin.length > 0 && pin.length !== 6)}
            onClick={() => void connect(phone)}
          >
            {language === "ar" ? "اختيار الرقم" : "Select number"}
          </Button>
        </Card>
      ))}
      {working && (
        <p className="muted-copy">
          <IconRefresh size={15} />{" "}
          {language === "ar"
            ? "جارٍ إكمال الربط مع Meta…"
            : "Completing the Meta connection…"}
        </p>
      )}
    </section>
  );
}
