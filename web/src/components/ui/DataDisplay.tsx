import type { ReactNode } from "react";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "error";
}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function StatCard({
  icon,
  label,
  value,
  foot,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  foot?: ReactNode;
}) {
  return (
    <section className="card stat-card">
      <div className="stat-head">
        <span>{label}</span>
        <span className="stat-icon">{icon}</span>
      </div>
      <div className="stat-value">{value}</div>
      {foot ? <div className="stat-foot">{foot}</div> : null}
    </section>
  );
}
