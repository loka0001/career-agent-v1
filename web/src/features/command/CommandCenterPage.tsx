import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import {
  IconAlertTriangle,
  IconChat,
  IconPlug,
  IconSpark,
  IconTrend,
} from "../../components/icons";
import { MotionPage, PageHeading } from "../../components/operations";
import {
  Alert,
  Badge,
  Button,
  Card,
  Spinner,
  StatCard,
} from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import type {
  AnalyticsSnapshot,
  ContentItem,
  ConversationSummary,
  OrderRecord,
  ProviderConnection,
  WhatsAppSettings,
} from "../../lib/types";

interface HomeData {
  conversations: ConversationSummary[] | null;
  content: ContentItem[] | null;
  connections: ProviderConnection[] | null;
  whatsapp: WhatsAppSettings | null;
  orders: OrderRecord[] | null;
  analytics: AnalyticsSnapshot | null;
}

type HomeSource = keyof HomeData;

const emptyData: HomeData = {
  conversations: null,
  content: null,
  connections: null,
  whatsapp: null,
  orders: null,
  analytics: null,
};

const sourceLabels: Record<HomeSource, { ar: string; en: string }> = {
  conversations: { ar: "المحادثات", en: "conversations" },
  content: { ar: "المحتوى", en: "content" },
  connections: { ar: "اتصالات Meta", en: "Meta connections" },
  whatsapp: { ar: "WhatsApp", en: "WhatsApp" },
  orders: { ar: "الطلبات", en: "orders" },
  analytics: { ar: "زمن الاستجابة", en: "response time" },
};

const channelNames: Record<string, { ar: string; en: string }> = {
  whatsapp: { ar: "WhatsApp", en: "WhatsApp" },
  instagram_dm: { ar: "رسائل Instagram", en: "Instagram DM" },
  messenger: { ar: "Messenger", en: "Messenger" },
  facebook_comments: { ar: "تعليقات Facebook", en: "Facebook comments" },
  instagram_comments: {
    ar: "تعليقات Instagram",
    en: "Instagram comments",
  },
  webchat: { ar: "محادثة الموقع", en: "Website chat" },
};

const requiredMetaConnectionTypes = [
  "facebook_page",
  "instagram_business",
] as const;

const orderActionStatuses = new Set([
  "draft",
  "pending",
  "confirmed",
  "paid",
  "processing",
]);

function awaitsMerchantReply(conversation: ConversationSummary): boolean {
  if (conversation.status !== "open" || !conversation.last_inbound_at) {
    return false;
  }
  if (!conversation.last_outbound_at) return true;
  return (
    new Date(conversation.last_inbound_at).getTime() >
    new Date(conversation.last_outbound_at).getTime()
  );
}

function metaConnectionHealthy(
  connections: ProviderConnection[],
  connectionType: (typeof requiredMetaConnectionTypes)[number],
): boolean {
  return connections.some(
    (connection) =>
      connection.provider === "meta" &&
      connection.connection_type === connectionType &&
      connection.status === "connected" &&
      !connection.token_expiring,
  );
}

function whatsappHealthy(whatsapp: WhatsAppSettings): boolean {
  return (
    whatsapp.configured &&
    whatsapp.is_active &&
    (whatsapp.mode === "demo" || whatsapp.connection_status === "connected")
  );
}

export function CommandCenterPage() {
  const { language } = useLanguage();
  const [data, setData] = useState<HomeData>(emptyData);
  const [failedSources, setFailedSources] = useState<HomeSource[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.conversations(),
      api.studioContent(),
      api.providerConnections(),
      api.whatsappSettings(),
      api.orders(),
      api.analytics(),
    ]);
    const [
      conversationsResult,
      contentResult,
      connectionsResult,
      whatsappResult,
      ordersResult,
      analyticsResult,
    ] = results;
    const next: HomeData = {
      conversations:
        conversationsResult.status === "fulfilled"
          ? conversationsResult.value.conversations
          : null,
      content:
        contentResult.status === "fulfilled" ? contentResult.value : null,
      connections:
        connectionsResult.status === "fulfilled"
          ? connectionsResult.value
          : null,
      whatsapp:
        whatsappResult.status === "fulfilled" ? whatsappResult.value : null,
      orders: ordersResult.status === "fulfilled" ? ordersResult.value : null,
      analytics:
        analyticsResult.status === "fulfilled" ? analyticsResult.value : null,
    };
    const failures: HomeSource[] = [];
    if (conversationsResult.status === "rejected")
      failures.push("conversations");
    if (contentResult.status === "rejected") failures.push("content");
    if (connectionsResult.status === "rejected") failures.push("connections");
    if (whatsappResult.status === "rejected") failures.push("whatsapp");
    if (ordersResult.status === "rejected") failures.push("orders");
    if (analyticsResult.status === "rejected") failures.push("analytics");
    setData(next);
    setFailedSources(failures);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const copy =
    language === "ar"
      ? {
          title: "مركز القيادة",
          body: "ما يحتاج انتباهك الآن، من بيانات المتجر الفعلية.",
          loading: "جارٍ تجهيز ملخص المتجر…",
          partialError: "تعذر تحميل بعض بيانات المتجر",
          retry: "إعادة المحاولة",
          attention: "يحتاج انتباهك",
          waitingReplies: "محادثات تنتظر ردًا",
          overdue: "متأخرة عن وقت الاستجابة",
          noOverdue: "لا توجد محادثات متأخرة",
          latestLimit: "من أحدث 100 محادثة",
          contentReview: "محتوى ينتظر المراجعة",
          drafts: "مسودات سليمة تحتاج قرار التاجر",
          publishingAttention: "نشر يحتاج تدخلاً",
          reviewBeforeRetry: "فشل أو حالة غير مؤكدة تحتاج مراجعة",
          channelSetup: "قنوات تحتاج إعدادًا",
          requiredChannels: "Facebook وInstagram وWhatsApp",
          whoIsWaiting: "من ينتظر ردك؟",
          inbox: "فتح صندوق الوارد",
          noWaiting: "لا توجد محادثات تنتظر ردًا الآن.",
          overdueBadge: "متأخرة",
          unread: "غير مقروء",
          review: "راجع",
          outcomes: "نتائج حديثة",
          replied: "محادثات تم الرد عليها",
          repliedFoot: "ضمن أحدث 100 محادثة",
          published: "محتوى منشور",
          publishedFoot: "من سجلات استوديو المحتوى",
          activeOrders: "طلبات نشطة",
          activeOrdersFoot: "ضمن أحدث 200 طلب",
          responseTime: "متوسط أول رد",
          responseTimeFoot: "ضمن فترة التحليلات الحالية",
          unavailable: "غير متاح",
          minute: "د",
          actions: "إجراءات سريعة",
          createContent: "إنشاء محتوى",
          integrations: "فحص التكاملات",
          products: "إدارة المنتجات",
        }
      : {
          title: "Command Center",
          body: "What needs your attention now, backed by live store data.",
          loading: "Preparing your store summary…",
          partialError: "Some live store data could not be loaded",
          retry: "Try again",
          attention: "Needs attention",
          waitingReplies: "Conversations awaiting reply",
          overdue: "Overdue for a response",
          noOverdue: "No conversations are overdue",
          latestLimit: "From the latest 100 conversations",
          contentReview: "Content awaiting review",
          drafts: "Valid drafts requiring a merchant decision",
          publishingAttention: "Publishing needs attention",
          reviewBeforeRetry: "Failed or uncertain outcomes need review",
          channelSetup: "Channels requiring setup",
          requiredChannels: "Facebook, Instagram, and WhatsApp",
          whoIsWaiting: "Who is waiting for a reply?",
          inbox: "Open Inbox",
          noWaiting: "No conversations are awaiting a reply right now.",
          overdueBadge: "Overdue",
          unread: "unread",
          review: "Review",
          outcomes: "Recent outcomes",
          replied: "Conversations with replies",
          repliedFoot: "Within the latest 100 conversations",
          published: "Published content",
          publishedFoot: "From Content Studio records",
          activeOrders: "Active orders",
          activeOrdersFoot: "Within the latest 200 orders",
          responseTime: "Average first response",
          responseTimeFoot: "For the current analytics period",
          unavailable: "Unavailable",
          minute: "min",
          actions: "Quick actions",
          createContent: "Create content",
          integrations: "Check integrations",
          products: "Manage products",
        };

  const derived = useMemo(() => {
    const waitingReplies = (data.conversations ?? []).filter(
      awaitsMerchantReply,
    );
    const overdueCount = waitingReplies.filter(
      (conversation) => conversation.sla_overdue,
    ).length;
    const reviewableDrafts = (data.content ?? []).filter(
      (item) =>
        item.status === "draft" && item.validation_warnings.length === 0,
    );
    const publishingAttention = (data.content ?? []).filter((item) =>
      ["failed", "partial", "publish_unknown"].includes(item.status),
    );
    const missingMetaChannels = data.connections
      ? requiredMetaConnectionTypes.filter(
          (type) => !metaConnectionHealthy(data.connections ?? [], type),
        ).length
      : 0;
    const whatsappNeedsSetup = data.whatsapp
      ? whatsappHealthy(data.whatsapp)
        ? 0
        : 1
      : 0;
    const conversationsWithReplies = (data.conversations ?? []).filter(
      (conversation) => conversation.last_outbound_at !== null,
    ).length;
    const publishedContent = (data.content ?? []).filter(
      (item) => item.status === "published",
    ).length;
    const activeOrders = (data.orders ?? []).filter((order) =>
      orderActionStatuses.has(order.status),
    ).length;
    return {
      waitingReplies,
      overdueCount,
      reviewableDrafts,
      publishingAttention,
      channelSetupCount: missingMetaChannels + whatsappNeedsSetup,
      conversationsWithReplies,
      publishedContent,
      activeOrders,
    };
  }, [data]);

  const failedSourceText = failedSources
    .map((source) => sourceLabels[source][language])
    .join(", ");

  if (loading && Object.values(data).every((value) => value === null)) {
    return <Spinner label={copy.loading} />;
  }

  return (
    <MotionPage>
      <PageHeading title={copy.title} description={copy.body} />
      {failedSources.length > 0 ? (
        <Alert tone="error">
          {copy.partialError}: {failedSourceText}.{" "}
          <Button variant="ghost" onClick={load} disabled={loading}>
            {copy.retry}
          </Button>
        </Alert>
      ) : null}

      <section aria-labelledby="attention-title">
        <div className="section-heading">
          <h2 id="attention-title">{copy.attention}</h2>
        </div>
        <div className="stats-grid">
          <StatCard
            icon={<IconChat />}
            label={copy.waitingReplies}
            value={
              data.conversations
                ? derived.waitingReplies.length
                : copy.unavailable
            }
            foot={
              data.conversations
                ? derived.overdueCount
                  ? `${derived.overdueCount} ${copy.overdue}`
                  : `${copy.noOverdue} · ${copy.latestLimit}`
                : copy.unavailable
            }
          />
          <StatCard
            icon={<IconSpark />}
            label={copy.contentReview}
            value={
              data.content ? derived.reviewableDrafts.length : copy.unavailable
            }
            foot={data.content ? copy.drafts : copy.unavailable}
          />
          <StatCard
            icon={<IconAlertTriangle />}
            label={copy.publishingAttention}
            value={
              data.content
                ? derived.publishingAttention.length
                : copy.unavailable
            }
            foot={data.content ? copy.reviewBeforeRetry : copy.unavailable}
          />
          <StatCard
            icon={<IconPlug />}
            label={copy.channelSetup}
            value={
              data.connections && data.whatsapp
                ? derived.channelSetupCount
                : copy.unavailable
            }
            foot={
              data.connections && data.whatsapp
                ? copy.requiredChannels
                : copy.unavailable
            }
          />
        </div>
      </section>

      <div className="operations-grid command-priority-grid">
        <Card className="decision-panel">
          <div className="panel-head">
            <h2>
              <IconChat size={18} /> {copy.whoIsWaiting}
            </h2>
            <Link to="/app/inbox">{copy.inbox}</Link>
          </div>
          <div className="decision-list">
            {derived.waitingReplies.slice(0, 5).map((conversation) => (
              <div className="decision-row" key={conversation.id}>
                <div className="grow">
                  <span className="row-title">
                    {conversation.customer.display_name}
                    {conversation.sla_overdue ? (
                      <Badge tone="error">{copy.overdueBadge}</Badge>
                    ) : null}
                  </span>
                  <small>
                    {channelNames[conversation.channel_type]?.[language] ??
                      conversation.channel_type}
                    {conversation.unread_count
                      ? ` · ${conversation.unread_count} ${copy.unread}`
                      : ""}
                  </small>
                </div>
                <Link
                  className="button button--secondary compact-action"
                  to="/app/inbox"
                >
                  {copy.review}
                </Link>
              </div>
            ))}
            {data.conversations && derived.waitingReplies.length === 0 ? (
              <p className="muted-copy">{copy.noWaiting}</p>
            ) : null}
            {!data.conversations ? (
              <p className="muted-copy">{copy.unavailable}</p>
            ) : null}
          </div>
        </Card>

        <Card>
          <div className="panel-head">
            <h2>
              <IconTrend size={18} /> {copy.outcomes}
            </h2>
          </div>
          <div className="command-outcomes">
            <StatCard
              icon={<IconChat />}
              label={copy.replied}
              value={
                data.conversations
                  ? derived.conversationsWithReplies
                  : copy.unavailable
              }
              foot={data.conversations ? copy.repliedFoot : copy.unavailable}
            />
            <StatCard
              icon={<IconSpark />}
              label={copy.published}
              value={data.content ? derived.publishedContent : copy.unavailable}
              foot={data.content ? copy.publishedFoot : copy.unavailable}
            />
            <StatCard
              icon={<IconTrend />}
              label={copy.activeOrders}
              value={data.orders ? derived.activeOrders : copy.unavailable}
              foot={data.orders ? copy.activeOrdersFoot : copy.unavailable}
            />
            <StatCard
              icon={<IconChat />}
              label={copy.responseTime}
              value={
                data.analytics?.first_response_minutes !== null &&
                data.analytics?.first_response_minutes !== undefined
                  ? `${data.analytics.first_response_minutes} ${copy.minute}`
                  : copy.unavailable
              }
              foot={data.analytics ? copy.responseTimeFoot : copy.unavailable}
            />
          </div>
        </Card>
      </div>

      <Card>
        <div className="panel-head">
          <h2>{copy.actions}</h2>
        </div>
        <div className="quick-actions">
          <Link className="button button--secondary" to="/app/inbox">
            {copy.inbox}
          </Link>
          <Link className="button button--secondary" to="/app/studio">
            {copy.createContent}
          </Link>
          <Link className="button button--secondary" to="/app/integrations">
            {copy.integrations}
          </Link>
          <Link className="button button--secondary" to="/app/products">
            {copy.products}
          </Link>
        </div>
      </Card>
    </MotionPage>
  );
}
