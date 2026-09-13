import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useAuth } from "../../app/AuthContext";
import {
  IconCheck,
  IconKey,
  IconSpark,
  IconUsers,
} from "../../components/icons";
import { AuthBrandPanel } from "../../components/layout/AuthBrandPanel";
import { Alert, Button, Card, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { ApiError, api } from "../../lib/api";

function message(reason: unknown): string {
  return reason instanceof ApiError ? reason.message : "تعذر تنفيذ الطلب.";
}

function AuthFrame({
  title,
  description,
  children,
  split = false,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  split?: boolean;
}) {
  const { language } = useLanguage();
  return (
    <main
      className={`auth-page ${split ? "auth-page--split" : ""}`}
      dir={language === "ar" ? "rtl" : "ltr"}
    >
      <div className="aurora" aria-hidden="true" />
      {split ? <AuthBrandPanel language={language} /> : null}
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
        <h1>{title}</h1>
        <p>{description}</p>
        {children}
      </Card>
    </main>
  );
}

export function SignupPage() {
  const { language } = useLanguage();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [form, setForm] = useState({
    organization_name: "",
    store_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [pendingEmail, setPendingEmail] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (form.password !== confirmPassword) {
      setError(
        language === "ar"
          ? "كلمتا المرور غير متطابقتين."
          : "Passwords do not match.",
      );
      return;
    }
    if (!termsAccepted) {
      setError(
        language === "ar"
          ? "يجب الموافقة على الشروط وسياسة الخصوصية."
          : "You must accept the Terms and Privacy Policy.",
      );
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await api.register(form);
      if (result.verification_required) {
        setPendingEmail(result.email);
      } else {
        await refresh();
        navigate("/app/onboarding");
      }
    } catch (reason) {
      setError(message(reason));
    } finally {
      setLoading(false);
    }
  }

  if (pendingEmail) {
    return (
      <AuthFrame
        title={language === "ar" ? "راجع بريدك الإلكتروني" : "Check your email"}
        description={
          language === "ar"
            ? `أرسلنا رابط تفعيل أحادي الاستخدام إلى ${pendingEmail}.`
            : `We sent a one-time activation link to ${pendingEmail}.`
        }
      >
        <Alert tone="success">
          {language === "ar"
            ? "لن يعمل الحساب قبل تأكيد البريد."
            : "The account remains inactive until email verification."}
        </Alert>
        <Button
          variant="secondary"
          onClick={() => void api.resendVerification(pendingEmail)}
        >
          {language === "ar" ? "إعادة إرسال الرابط" : "Resend link"}
        </Button>
        <Link className="button button--ghost" to="/login">
          {language === "ar" ? "العودة للدخول" : "Back to sign in"}
        </Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      split
      title={
        language === "ar"
          ? "أنشئ مساحة بيع حقيقية"
          : "Create a real commerce workspace"
      }
      description={
        language === "ar"
          ? "بيانات المالك والمتجر، ثم نتحقق من البريد قبل فتح لوحة التحكم. الوصول الحالي مجاني ولا يحتاج بطاقة."
          : "Enter owner and store details, then verify email before access. Current access is free and needs no card."
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <Alert tone="info">
        <IconCheck size={16} />{" "}
        {language === "ar"
          ? "لا وسيلة دفع ولا اشتراك مدفوع في المرحلة الحالية."
          : "No payment method or paid subscription at this stage."}
      </Alert>
      <form onSubmit={submit}>
        <label>
          {language === "ar" ? "اسمك" : "Your name"}
          <input
            value={form.full_name}
            onChange={(event) =>
              setForm({ ...form, full_name: event.target.value })
            }
            required
          />
        </label>
        <label>
          {language === "ar" ? "اسم الشركة" : "Company name"}
          <input
            value={form.organization_name}
            onChange={(event) =>
              setForm({ ...form, organization_name: event.target.value })
            }
            required
          />
        </label>
        <label>
          {language === "ar" ? "اسم المتجر" : "Store name"}
          <input
            value={form.store_name}
            onChange={(event) =>
              setForm({ ...form, store_name: event.target.value })
            }
            required
          />
        </label>
        <label>
          {language === "ar" ? "البريد الإلكتروني" : "Email"}
          <input
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(event) =>
              setForm({ ...form, email: event.target.value })
            }
            required
          />
        </label>
        <label>
          {language === "ar" ? "كلمة المرور" : "Password"}
          <input
            type="password"
            autoComplete="new-password"
            minLength={10}
            value={form.password}
            onChange={(event) =>
              setForm({ ...form, password: event.target.value })
            }
            required
          />
        </label>
        <div
          className="password-strength"
          aria-label={
            language === "ar" ? "قوة كلمة المرور" : "Password strength"
          }
        >
          {[10, 12, 14, 16].map((threshold) => (
            <span
              key={threshold}
              className={form.password.length >= threshold ? "active" : ""}
            />
          ))}
        </div>
        <small className="field-help">
          {language === "ar"
            ? "10 أحرف على الأقل، مع حروف كبيرة وصغيرة وأرقام أو رموز."
            : "At least 10 characters with upper/lowercase letters and numbers or symbols."}
        </small>
        <label>
          {language === "ar" ? "تأكيد كلمة المرور" : "Confirm password"}
          <input
            type="password"
            autoComplete="new-password"
            minLength={10}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            aria-invalid={Boolean(
              confirmPassword && confirmPassword !== form.password,
            )}
            required
          />
          {confirmPassword && confirmPassword !== form.password ? (
            <small className="field-error">
              {language === "ar"
                ? "كلمتا المرور غير متطابقتين."
                : "Passwords do not match."}
            </small>
          ) : null}
        </label>
        <label className="terms-control">
          <input
            type="checkbox"
            checked={termsAccepted}
            onChange={(event) => setTermsAccepted(event.target.checked)}
            required
          />
          <span>
            {language === "ar" ? "أوافق على " : "I agree to the "}
            <Link to="/terms">{language === "ar" ? "الشروط" : "Terms"}</Link>
            {language === "ar" ? " وسياسة الخصوصية" : " and Privacy Policy"}
          </span>
        </label>
        <Button type="submit" disabled={loading}>
          {loading
            ? language === "ar"
              ? "جارٍ الإنشاء…"
              : "Creating…"
            : language === "ar"
              ? "إنشاء الحساب"
              : "Create account"}
        </Button>
      </form>
      <div className="auth-links">
        <Link to="/login">
          {language === "ar"
            ? "لديك حساب؟ سجل الدخول"
            : "Already have an account? Sign in"}
        </Link>
      </div>
    </AuthFrame>
  );
}

export function VerifyEmailPage() {
  const { language } = useLanguage();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [error, setError] = useState("");
  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("رابط التفعيل غير مكتمل.");
      return;
    }
    api
      .verifyEmail(token)
      .then(async () => {
        await refresh();
        navigate("/app/onboarding", { replace: true });
      })
      .catch((reason) => setError(message(reason)));
  }, [navigate, params, refresh]);
  return (
    <AuthFrame
      title={language === "ar" ? "تأكيد البريد" : "Verify email"}
      description={
        language === "ar"
          ? "نتحقق من الرابط الآمن الآن."
          : "Verifying the secure link now."
      }
    >
      {error ? (
        <Alert tone="error">{error}</Alert>
      ) : (
        <Spinner label="جارٍ تفعيل الحساب…" />
      )}
      {error && (
        <Link className="button button--secondary" to="/login">
          العودة للدخول
        </Link>
      )}
    </AuthFrame>
  );
}

export function ForgotPasswordPage() {
  const { language } = useLanguage();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (reason) {
      setError(message(reason));
    }
  }
  return (
    <AuthFrame
      title={language === "ar" ? "استعادة كلمة المرور" : "Recover password"}
      description={
        language === "ar"
          ? "سنرسل رابطًا صالحًا لمدة ساعة إن كان الحساب موجودًا."
          : "We send a one-hour link if the account exists."
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      {sent ? (
        <Alert tone="success">
          راجع بريدك. تظهر النتيجة نفسها لحماية خصوصية الحسابات.
        </Alert>
      ) : (
        <form onSubmit={submit}>
          <label>
            البريد الإلكتروني
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <Button type="submit">
            <IconKey size={17} /> إرسال رابط الاستعادة
          </Button>
        </form>
      )}
      <div className="auth-links">
        <Link to="/login">العودة للدخول</Link>
      </div>
    </AuthFrame>
  );
}

export function ResetPasswordPage() {
  const { language } = useLanguage();
  const [params] = useSearchParams();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    const token = params.get("token");
    if (!token) {
      setError("رابط الاستعادة غير مكتمل.");
      return;
    }
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (reason) {
      setError(message(reason));
    }
  }
  return (
    <AuthFrame
      title={language === "ar" ? "كلمة مرور جديدة" : "New password"}
      description={
        language === "ar"
          ? "سيتم إلغاء كل الجلسات السابقة بعد الحفظ."
          : "All previous sessions are revoked after saving."
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      {done ? (
        <>
          <Alert tone="success">
            <IconCheck size={16} /> تم تحديث كلمة المرور.
          </Alert>
          <Link className="button button--primary" to="/login">
            تسجيل الدخول
          </Link>
        </>
      ) : (
        <form onSubmit={submit}>
          <label>
            كلمة المرور الجديدة
            <input
              type="password"
              autoComplete="new-password"
              minLength={10}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <Button type="submit">تحديث وإلغاء الجلسات</Button>
        </form>
      )}
    </AuthFrame>
  );
}

export function AcceptInvitePage() {
  const { language } = useLanguage();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const token = params.get("token");
    if (!token) {
      setError("رابط الدعوة غير مكتمل.");
      return;
    }
    setLoading(true);
    try {
      await api.acceptInvite(token, password, fullName);
      await refresh();
      navigate("/app/command", { replace: true });
    } catch (reason) {
      setError(message(reason));
    } finally {
      setLoading(false);
    }
  }
  return (
    <AuthFrame
      title={language === "ar" ? "قبول دعوة الفريق" : "Accept team invitation"}
      description={
        language === "ar"
          ? "اختر بيانات دخولك بنفسك؛ لا توجد كلمات مرور مؤقتة."
          : "Choose your own credentials; there are no temporary passwords."
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <form onSubmit={submit}>
        <label>
          الاسم
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </label>
        <label>
          كلمة المرور
          <input
            type="password"
            autoComplete="new-password"
            minLength={10}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <Button type="submit" disabled={loading}>
          <IconUsers size={17} />{" "}
          {loading ? "جارٍ الانضمام…" : "قبول والانضمام"}
        </Button>
      </form>
    </AuthFrame>
  );
}
