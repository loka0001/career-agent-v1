import type { ReactNode } from "react";

export function Alert({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "success" | "warning" | "error";
}) {
  return (
    <div
      className={`alert alert--${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="spinner" role="status">
      <span aria-hidden="true" />
      {label}
    </span>
  );
}

export function Skeleton({
  height = "1rem",
  className = "",
}: {
  height?: string;
  className?: string;
}) {
  return (
    <div
      className={`skeleton ${className}`.trim()}
      style={{ height }}
      aria-hidden="true"
    />
  );
}
