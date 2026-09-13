import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { useAuth } from "../../app/AuthContext";
import {
  IconEye,
  IconEyeOff,
  IconShield,
  IconSpark,
} from "../../components/icons";
import { AuthBrandPanel } from "../../components/layout/AuthBrandPanel";
import { Alert, Button, Card } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { ApiError } from "../../lib/api";

export function LoginPage() {
  const { user, login } = useAuth();
  const { language } = useLanguage();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session-expired";
  const [email, setEmail] = useState(
    () => window.localStorage.getItem("commerce-login-email") ?? "",
  );
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(() =>
    Boolean(window.localStorage.getItem("commerce-login-email")),
  );
  const [otp, setOtp] = useState("");
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to="/app/command" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password, needsMfa ? otp : undefined);
      if (remember) window.localStorage.setItem("commerce-login-email", email);
      else window.localStorage.removeItem("commerce-login-email");
      navigate("/app/command");
    } catch (reason) {
      if (reason instanceof ApiError && reason.body.code === "mfa_required") {
        setNeedsMfa(true);
      } else {
        setError(
          reason instanceof ApiError
            ? reason.message
            : language === "ar"
              ? "تعذر الاتصال بالخادم."
              : "Unable to connect to the server.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="auth-page auth-page--split"
      dir={language === "ar" ? "rtl" : "ltr"}
    >
      <div className="aurora" aria-hidden="true" />
      <AuthBrandPanel language={language} />
      <Card className="auth-card">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <IconSpark size={17} />
          </span>
          <span className="brand-copy">
            <b>Commerce</b>
            <small>Revenue Autopilot</small>
          </span>
        </Link>
        <h1>
          {needsMfa
            ? language === "ar"
              ? "التحقق بخطوتين"
              : "Two-factor verification"
            : language === "ar"
              ? "دخول مساحة العمل"
              : "Sign in to workspace"}
        </h1>
        <p>
          {needsMfa
            ? language === "ar"
              ? "أدخل الرمز الحالي من تطبيق المصادقة لإكمال الدخول."
              : "Enter the current code from your authenticator app."
            : language === "ar"
              ? "استخدم حسابك للوصول إلى المتجر والمحادثات والتقارير."
              : "Use your account to access store operations, inbox, and reports."}
        </p>
        {sessionExpired && (
          <Alert tone="warning">
            {language === "ar"
              ? "انتهت جلستك. سجّل الدخول مرة أخرى للمتابعة."
              : "Your session expired. Sign in again to continue."}
          </Alert>
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <form onSubmit={submit}>
          {!needsMfa && (
            <>
              <label>
                {language === "ar" ? "البريد الإلكتروني" : "Email"}
                <input
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>
              <label>
                {language === "ar" ? "كلمة المرور" : "Password"}
                <span className="password-field">
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={
                      showPassword
                        ? language === "ar"
                          ? "إخفاء كلمة المرور"
                          : "Hide password"
                        : language === "ar"
                          ? "إظهار كلمة المرور"
                          : "Show password"
                    }
                  >
                    {showPassword ? (
                      <IconEyeOff size={18} />
                    ) : (
                      <IconEye size={18} />
                    )}
                  </button>
                </span>
              </label>
              <label className="remember-control">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                <span>
                  {language === "ar" ? "تذكر البريد" : "Remember email"}
                </span>
              </label>
            </>
          )}
          {needsMfa && (
            <label>
              {language === "ar" ? "رمز التحقق" : "Verification code"}
              <input
                className="otp-input"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={otp}
                onChange={(event) =>
                  setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                }
                pattern="\d{6}"
                required
                autoFocus
              />
            </label>
          )}
          <Button
            type="submit"
            disabled={loading || (needsMfa && otp.length !== 6)}
          >
            {needsMfa && <IconShield size={17} />}
            {loading
              ? language === "ar"
                ? "جارٍ التحقق…"
                : "Verifying…"
              : needsMfa
                ? language === "ar"
                  ? "تأكيد ودخول"
                  : "Verify and sign in"
                : language === "ar"
                  ? "دخول إلى اللوحة"
                  : "Sign in"}
          </Button>
          {needsMfa && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setNeedsMfa(false);
                setOtp("");
              }}
            >
              {language === "ar"
                ? "العودة لبيانات الدخول"
                : "Back to credentials"}
            </Button>
          )}
        </form>
        <div className="auth-links">
          <Link to="/forgot-password">
            {language === "ar" ? "نسيت كلمة المرور؟" : "Forgot password?"}
          </Link>
          <Link to="/signup">
            {language === "ar" ? "إنشاء متجر جديد" : "Create a new store"}
          </Link>
        </div>
      </Card>
    </main>
  );
}
