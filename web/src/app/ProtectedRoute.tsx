import { Link, Navigate } from "react-router";
import { Spinner } from "../components/ui";
import { useLanguage } from "../i18n";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, sessionExpired } = useAuth();
  if (loading)
    return (
      <main className="center">
        <Spinner label="جارٍ التحقق…" />
      </main>
    );
  if (!user)
    return (
      <Navigate
        to={sessionExpired ? "/login?reason=session-expired" : "/login"}
        replace
      />
    );
  return children;
}

function AccessDenied({ reason }: { reason: "feature" | "operator" }) {
  const { language } = useLanguage();
  const isArabic = language === "ar";
  return (
    <section className="empty-state" aria-labelledby="access-denied-title">
      <h1 id="access-denied-title">
        {isArabic ? "الوصول غير مسموح" : "Access denied"}
      </h1>
      <p>
        {reason === "operator"
          ? isArabic
            ? "لا يتضمن دورك صلاحية الوصول إلى أدوات المشغّل."
            : "Your role does not include operator access."
          : isArabic
            ? "لا تتضمن خطتك الحالية هذه الميزة."
            : "Your current plan does not include this feature."}
      </p>
      <Link className="button button--secondary" to="/app/command">
        {isArabic ? "العودة إلى الرئيسية" : "Return to Home"}
      </Link>
    </section>
  );
}

export function EntitledRoute({
  feature,
  children,
}: {
  feature: string;
  children: React.ReactNode;
}) {
  const { subscription, loading } = useAuth();
  if (loading)
    return (
      <main className="center">
        <Spinner label="جاري التحقق…" />
      </main>
    );
  if (!subscription?.plan.features.includes(feature)) {
    return <AccessDenied reason="feature" />;
  }
  return children;
}

export function OperatorRoute({ children }: { children: React.ReactNode }) {
  const { isOperator, loading } = useAuth();
  if (loading)
    return (
      <main className="center">
        <Spinner label="جاري التحقق…" />
      </main>
    );
  if (!isOperator) return <AccessDenied reason="operator" />;
  return children;
}
