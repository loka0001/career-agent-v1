import { IconChart, IconShield, IconSpark } from "../icons";
import { Brand } from "./Brand";

export function AuthBrandPanel({ language }: { language: "ar" | "en" }) {
  return (
    <aside className="auth-brand-panel" aria-label="Commerce Revenue Autopilot">
      <Brand />
      <div className="auth-brand-panel__copy">
        <span className="eyebrow">
          <IconSpark size={16} />
          {language === "ar"
            ? "تشغيل موحّد للتجارة"
            : "Unified commerce operations"}
        </span>
        <h2>
          {language === "ar"
            ? "حوّل كل إشارة إلى قرار واضح وقابل للتنفيذ."
            : "Turn every signal into a clear, actionable decision."}
        </h2>
        <p>
          {language === "ar"
            ? "المحادثات والطلبات والتحليلات والأتمتة في مساحة آمنة واحدة."
            : "Conversations, orders, analytics, and automation in one secure workspace."}
        </p>
      </div>
      <div className="auth-brand-panel__facts">
        <span>
          <IconChart size={19} />
          {language === "ar"
            ? "قرارات مبنية على بيانات حقيقية"
            : "Decisions grounded in real data"}
        </span>
        <span>
          <IconShield size={19} />
          {language === "ar"
            ? "تحكم ومراجعة قبل التنفيذ"
            : "Control and review before execution"}
        </span>
      </div>
    </aside>
  );
}
