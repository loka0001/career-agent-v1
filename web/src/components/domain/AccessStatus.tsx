import { IconCheck } from "../icons";

export function AccessStatus({
  language,
  compact = false,
}: {
  language: "ar" | "en";
  compact?: boolean;
}) {
  return (
    <span
      className={`access-status ${compact ? "access-status--compact" : ""}`}
    >
      <IconCheck size={14} />
      {language === "ar" ? "وصول مجاني · بلا بطاقة" : "Free access · no card"}
    </span>
  );
}

export function DemoStatus({
  language,
  compact = false,
}: {
  language: "ar" | "en";
  compact?: boolean;
}) {
  return (
    <span className={`demo-status ${compact ? "demo-status--compact" : ""}`}>
      {language === "ar"
        ? "بيئة تجريبية · بيانات معزولة"
        : "Demo · isolated data"}
    </span>
  );
}
