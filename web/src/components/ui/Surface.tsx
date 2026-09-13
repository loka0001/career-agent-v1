import type { ComponentPropsWithoutRef, ReactNode } from "react";

export function Card({
  children,
  className = "",
  hover = false,
  ...sectionProps
}: ComponentPropsWithoutRef<"section"> & {
  hover?: boolean;
}) {
  return (
    <section
      {...sectionProps}
      className={`card ${hover ? "card--hover" : ""} ${className}`.trim()}
    >
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <Card className="empty-state">
      <h2>{title}</h2>
      <p>{body}</p>
      {action}
    </Card>
  );
}
