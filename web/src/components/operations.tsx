import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { ApiError } from "../lib/api";
import { IconSpark } from "./icons";

export function errorText(
  reason: unknown,
  language: "ar" | "en" = "ar",
): string {
  return reason instanceof ApiError
    ? reason.message
    : language === "ar"
      ? "تعذر تحميل البيانات. حاول مرة أخرى."
      : "Data could not be loaded. Try again.";
}

export function MotionPage({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduced ? undefined : { opacity: 0, y: -6 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

export function PageHeading({
  title,
  description,
  action,
  eyebrow = "Revenue Autopilot",
}: {
  title: string;
  description: string;
  action?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">
          <IconSpark size={14} /> {eyebrow}
        </span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function ProgressBar({
  value,
  max = 100,
  label,
}: {
  value: number;
  max?: number;
  label: string;
}) {
  const safeMax = Math.max(max, 1);
  const percent = Math.min(100, Math.max(0, (value / safeMax) * 100));
  return (
    <div className="progress-row">
      <span>
        {label}
        <b>
          {value}/{max < 0 ? "∞" : max}
        </b>
      </span>
      <div
        className="progress-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max < 0 ? undefined : max}
        aria-valuenow={value}
      >
        <motion.span
          initial={{ scaleX: 0 }}
          animate={{ scaleX: percent / 100 }}
        />
      </div>
    </div>
  );
}

export function Pipeline({
  items,
}: {
  items: { label: string; value: number }[];
}) {
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <div className="pipeline" aria-label="Conversion pipeline">
      {items.map((item, index) => (
        <motion.div
          key={item.label}
          className="pipeline-stage"
          initial={{ opacity: 0, scaleX: 0.85 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: index * 0.06 }}
          style={{ inlineSize: `${Math.max(38, (item.value / max) * 100)}%` }}
        >
          <span>{item.label}</span>
          <b>{item.value}</b>
        </motion.div>
      ))}
    </div>
  );
}
