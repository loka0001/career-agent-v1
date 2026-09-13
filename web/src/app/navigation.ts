import type { ComponentType } from "react";
import {
  IconBox,
  IconCalendar,
  IconChart,
  IconChat,
  IconDashboard,
  IconKey,
  IconPlug,
  IconReceipt,
  IconSettings,
  IconShield,
  IconSpark,
  IconTarget,
  IconUsers,
  IconWorkflow,
} from "../components/icons";

export interface NavigationItem {
  to: string;
  ar: string;
  en: string;
  icon: ComponentType<{ size?: number }>;
  feature?: string;
  operator?: boolean;
}

export interface NavigationGroup {
  ar: string;
  en: string;
  items: NavigationItem[];
}

export const primaryNavigationItems: NavigationItem[] = [
  {
    to: "/app/command",
    ar: "مركز القيادة",
    en: "Command Center",
    icon: IconDashboard,
  },
  { to: "/app/inbox", ar: "الرسائل", en: "Inbox", icon: IconChat },
  {
    to: "/app/studio",
    ar: "استوديو المحتوى",
    en: "Content Studio",
    icon: IconSpark,
    feature: "content_studio",
  },
  {
    to: "/app/products",
    ar: "المنتجات",
    en: "Products",
    icon: IconBox,
    feature: "catalog",
  },
  {
    to: "/app/integrations",
    ar: "التكاملات",
    en: "Integrations",
    icon: IconPlug,
  },
  {
    to: "/app/settings",
    ar: "إعدادات المتجر",
    en: "Store Settings",
    icon: IconSettings,
  },
];

export const secondaryNavigationGroups: NavigationGroup[] = [
  {
    ar: "عمليات إضافية",
    en: "Additional operations",
    items: [
      {
        to: "/app/opportunities",
        ar: "فرص الإيراد",
        en: "Opportunities",
        icon: IconTarget,
        feature: "opportunities",
      },
      {
        to: "/app/customers",
        ar: "العملاء",
        en: "Customers",
        icon: IconUsers,
      },
      {
        to: "/app/orders",
        ar: "الطلبات",
        en: "Orders",
        icon: IconReceipt,
      },
    ],
  },
  {
    ar: "أدوات النمو",
    en: "Growth tools",
    items: [
      {
        to: "/app/calendar",
        ar: "تقويم الحملات",
        en: "Campaign Calendar",
        icon: IconCalendar,
        feature: "content_studio",
      },
      {
        to: "/app/analytics",
        ar: "التحليلات",
        en: "Analytics",
        icon: IconChart,
        feature: "analytics",
      },
      {
        to: "/app/automations",
        ar: "الأتمتة",
        en: "Automations",
        icon: IconWorkflow,
        feature: "automations",
      },
      {
        to: "/app/agent-settings",
        ar: "إعدادات المساعد",
        en: "Agent Settings",
        icon: IconSpark,
        feature: "inbox",
      },
    ],
  },
  {
    ar: "إدارة متقدمة",
    en: "Advanced management",
    items: [
      { to: "/app/team", ar: "الفريق", en: "Team", icon: IconUsers },
      {
        to: "/app/billing",
        ar: "الفوترة",
        en: "Billing",
        icon: IconReceipt,
      },
      {
        to: "/app/security",
        ar: "الأمان",
        en: "Security",
        icon: IconShield,
      },
      {
        to: "/app/api-keys",
        ar: "مفاتيح API",
        en: "API Keys",
        icon: IconKey,
        feature: "website_widget",
      },
      {
        to: "/app/privacy",
        ar: "الخصوصية والبيانات",
        en: "Privacy & Data",
        icon: IconShield,
      },
    ],
  },
];

export const navigationGroups: NavigationGroup[] = [
  { ar: "مساحة العمل", en: "Workspace", items: primaryNavigationItems },
  ...secondaryNavigationGroups,
];

export const operatorItem: NavigationItem = {
  to: "/app/operator",
  ar: "لوحة التشغيل",
  en: "Operator Console",
  icon: IconDashboard,
  operator: true,
};
