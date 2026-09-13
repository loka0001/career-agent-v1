import { useCallback, useEffect, useRef, useState } from "react";
import {
  IconChat,
  IconCheck,
  IconRefresh,
  IconSend,
  IconSpark,
} from "../../components/icons";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Skeleton,
} from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import { useLanguage } from "../../i18n";
import type {
  ConversationDetail,
  ConversationStatus,
  ConversationSummary,
  CustomerIntelligence,
  OrderRecord,
  SalesResponse,
} from "../../lib/types";
import {
  InboxContextRail,
  relatedOrdersForConversation,
} from "./InboxContextRail";
import { inboxCopy } from "./inboxCopy";
import { messageStatusLabel } from "./messageStatus";
import { SuggestionEvidence } from "./SuggestionEvidence";

const channelLabels: Record<string, { ar: string; en: string }> = {
  webchat: { ar: "شات الموقع", en: "Website chat" },
  whatsapp: { ar: "واتساب", en: "WhatsApp" },
  instagram_dm: { ar: "رسائل Instagram", en: "Instagram DM" },
  messenger: { ar: "Messenger", en: "Messenger" },
  facebook_comments: { ar: "تعليقات فيسبوك", en: "Facebook comments" },
  instagram_comments: { ar: "تعليقات إنستجرام", en: "Instagram comments" },
};

const statusFilters: { id: ConversationStatus | ""; ar: string; en: string }[] =
  [
    { id: "", ar: "الكل", en: "All" },
    { id: "open", ar: "مفتوحة", en: "Open" },
    { id: "pending", ar: "معلقة", en: "Pending" },
    { id: "resolved", ar: "منتهية", en: "Resolved" },
  ];

export function InboxPage() {
  const { language } = useLanguage();
  const copy = inboxCopy(language);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | "">("");
  const [selected, setSelected] = useState<ConversationDetail | null>(null);
  const [suggestion, setSuggestion] = useState<SalesResponse | null>(null);
  const [customerContext, setCustomerContext] =
    useState<CustomerIntelligence | null>(null);
  const [relatedOrders, setRelatedOrders] = useState<OrderRecord[]>([]);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState("");
  const [ordersUnavailable, setOrdersUnavailable] = useState(false);
  const [reply, setReply] = useState("");
  const [media, setMedia] = useState<File | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [demoAvailable, setDemoAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const timelineRef = useRef<HTMLDivElement>(null);
  const replyRequestRef = useRef<{
    conversationId: number;
    text: string;
    key: string;
  } | null>(null);
  const contextRequestRef = useRef(0);
  const selectionRef = useRef(0);
  const listRequestRef = useRef(0);
  const deliveryTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  useEffect(
    () => () => {
      ++selectionRef.current;
      ++contextRequestRef.current;
      ++listRequestRef.current;
      deliveryTimers.current.forEach(clearTimeout);
    },
    [],
  );

  const loadContext = useCallback(
    async (detail: ConversationDetail) => {
      const requestId = ++contextRequestRef.current;
      setContextLoading(true);
      setContextError("");
      const [customerResult, ordersResult] = await Promise.allSettled([
        api.customer(detail.customer.id),
        api.orders(),
      ]);
      if (contextRequestRef.current !== requestId) return;

      setCustomerContext(
        customerResult.status === "fulfilled" ? customerResult.value : null,
      );
      setOrdersUnavailable(ordersResult.status === "rejected");
      setRelatedOrders(
        ordersResult.status === "fulfilled"
          ? relatedOrdersForConversation(
              ordersResult.value,
              detail.customer.id,
              detail.id,
            )
          : [],
      );
      if (
        customerResult.status === "rejected" ||
        ordersResult.status === "rejected"
      ) {
        setContextError(copy.contextLoadError);
      }
      setContextLoading(false);
    },
    [copy.contextLoadError],
  );

  const loadList = useCallback(() => {
    const requestId = ++listRequestRef.current;
    setLoadingList(true);
    api
      .conversations({ status: statusFilter })
      .then((response) => {
        if (listRequestRef.current !== requestId) return;
        setConversations(response.conversations);
        setDemoAvailable(response.demo_available);
      })
      .catch(
        (reason) =>
          listRequestRef.current === requestId &&
          setError(
            reason instanceof ApiError ? reason.message : copy.loadError,
          ),
      )
      .finally(() => {
        if (listRequestRef.current === requestId) setLoadingList(false);
      });
  }, [copy, statusFilter]);
  useEffect(loadList, [loadList]);

  const openConversation = useCallback(
    (id: number) => {
      const selection = ++selectionRef.current;
      ++contextRequestRef.current;
      setSelected(null);
      setCustomerContext(null);
      setRelatedOrders([]);
      setOrdersUnavailable(false);
      setContextLoading(true);
      setContextError("");
      setSuggestion(null);
      setReply("");
      setMedia(null);
      setBusy(false);
      setNotice("");
      setError("");
      api
        .conversation(id)
        .then((detail) => {
          if (selectionRef.current !== selection) return;
          setSelected(detail);
          void loadContext(detail);
          setConversations((current) =>
            current.map((item) =>
              item.id === id ? { ...item, unread_count: 0 } : item,
            ),
          );
          requestAnimationFrame(() => {
            timelineRef.current?.scrollTo({
              top: timelineRef.current.scrollHeight,
            });
          });
        })
        .catch((reason) => {
          if (selectionRef.current !== selection) return;
          setContextLoading(false);
          setError(
            reason instanceof ApiError ? reason.message : copy.openError,
          );
        });
    },
    [copy, loadContext],
  );

  async function run(action: () => Promise<void>, success = "") {
    const selection = selectionRef.current;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      if (success && selectionRef.current === selection) setNotice(success);
    } catch (reason) {
      if (selectionRef.current !== selection) return;
      setError(
        reason instanceof ApiError
          ? `${reason.message} (${reason.body.code})`
          : copy.unexpectedError,
      );
    } finally {
      if (selectionRef.current === selection) setBusy(false);
    }
  }

  async function refreshConversation(id: number, selection: number) {
    if (selectionRef.current !== selection) return;
    try {
      const detail = await api.conversation(id);
      if (selectionRef.current !== selection) return;
      setSelected(detail);
      void loadContext(detail);
    } catch (reason) {
      if (selectionRef.current === selection)
        setError(reason instanceof ApiError ? reason.message : copy.openError);
    }
  }

  function sendReply() {
    if (!selected || !reply.trim()) return;
    const selection = selectionRef.current;
    const text = reply.trim();
    const previousRequest = replyRequestRef.current;
    const idempotencyKey =
      previousRequest?.conversationId === selected.id &&
      previousRequest.text === text
        ? previousRequest.key
        : `reply-${globalThis.crypto.randomUUID()}`;
    replyRequestRef.current = {
      conversationId: selected.id,
      text,
      key: idempotencyKey,
    };
    void run(async () => {
      await api.replyConversation(selected.id, text, idempotencyKey);
      if (replyRequestRef.current?.key === idempotencyKey)
        replyRequestRef.current = null;
      loadList();
      if (selectionRef.current !== selection) return;
      setReply("");
      // Delivery happens via the background worker within seconds.
      deliveryTimers.current.push(
        setTimeout(
          () => void refreshConversation(selected.id, selection),
          1200,
        ),
      );
      void refreshConversation(selected.id, selection);
    }, copy.replyQueued);
  }

  function sendMedia() {
    if (!selected || !media) return;
    const selection = selectionRef.current;
    void run(async () => {
      await api.sendWhatsAppMedia(selected.id, media, reply.trim());
      loadList();
      if (selectionRef.current !== selection) return;
      setMedia(null);
      setReply("");
      void refreshConversation(selected.id, selection);
    }, copy.mediaQueued);
  }

  function suggest() {
    if (!selected) return;
    const selection = selectionRef.current;
    void run(async () => {
      const result = await api.suggestReply(selected.id);
      if (selectionRef.current !== selection) return;
      setSuggestion(result);
      setReply(result.reply);
    }, copy.suggestionReady);
  }

  function setStatus(status: ConversationStatus) {
    if (!selected) return;
    const selection = selectionRef.current;
    void run(async () => {
      const updated = await api.updateConversation(selected.id, { status });
      loadList();
      if (selectionRef.current === selection) setSelected(updated);
    });
  }

  function simulate(text: string) {
    const selection = selectionRef.current;
    void run(async () => {
      const detail = await api.simulateInbound(text, copy.demoCustomer);
      loadList();
      if (selectionRef.current === selection) openConversation(detail.id);
    }, copy.demoMessageArrived);
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            <IconChat size={14} />{" "}
            {language === "ar"
              ? "صندوق موحد لكل القنوات"
              : "One inbox for every channel"}
          </span>
          <h1>{language === "ar" ? "المحادثات" : "Inbox"}</h1>
          <p>
            {language === "ar"
              ? "رد مقترح مؤسس على بياناتك، وإرسال حقيقي عبر القناة — أو تجريبي بأمان."
              : "Data-grounded suggestions and real channel delivery, or an explicitly safe demo."}
          </p>
        </div>
        <div className="quick-actions">
          <Button variant="secondary" onClick={loadList} disabled={loadingList}>
            <IconRefresh size={16} />
            {language === "ar" ? "تحديث" : "Refresh"}
          </Button>
        </div>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <div className="inbox-layout">
        <Card className="inbox-list">
          <div
            className="chip-row"
            role="group"
            aria-label={
              language === "ar" ? "تصفية حسب الحالة" : "Filter by status"
            }
          >
            {statusFilters.map((item) => (
              <button
                key={item.id || "all"}
                type="button"
                className={`chip ${statusFilter === item.id ? "active" : ""}`}
                aria-pressed={statusFilter === item.id}
                onClick={() => setStatusFilter(item.id)}
              >
                {item[language]}
              </button>
            ))}
          </div>
          {loadingList && (
            <div
              style={{ display: "grid", gap: "0.6rem", marginTop: "0.8rem" }}
            >
              {[1, 2, 3].map((key) => (
                <Skeleton key={key} height="4.2rem" />
              ))}
            </div>
          )}
          {!loadingList && conversations.length === 0 && (
            <EmptyState
              title={language === "ar" ? "لا توجد محادثات" : "No conversations"}
              body={
                demoAvailable
                  ? language === "ar"
                    ? "ابدأ محادثة تجريبية من الأزرار بالأسفل لرؤية الرحلة كاملة."
                    : "Start a clearly labelled demo conversation below to inspect the full flow."
                  : language === "ar"
                    ? "ستظهر رسائل القنوات والموقع هنا فور وصولها."
                    : "Channel and website messages appear here when they arrive."
              }
            />
          )}
          <div className="conversation-list">
            {conversations.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`conversation-row ${selected?.id === item.id ? "active" : ""}`}
                onClick={() => openConversation(item.id)}
              >
                <span className="avatar" aria-hidden="true">
                  {item.customer.display_name.slice(0, 1) ||
                    copy.avatarFallback}
                </span>
                <span className="grow">
                  <b>
                    {item.customer.display_name}
                    {item.sla_overdue && (
                      <Badge tone="error">{copy.overdue}</Badge>
                    )}
                    {item.unread_count > 0 && (
                      <Badge tone="warning">
                        {item.unread_count} {copy.newMessages}
                      </Badge>
                    )}
                  </b>
                  <small>{item.last_message_preview}</small>
                </span>
                <span className="meta">
                  <Badge>
                    {channelLabels[item.channel_type]?.[language] ??
                      item.channel_type}
                  </Badge>
                  <small>{formatDateTime(item.updated_at, language)}</small>
                </span>
              </button>
            ))}
          </div>
          {demoAvailable && (
            <div className="simulate-box">
              <p className="field-hint">
                {language === "ar"
                  ? "محاكاة رسالة عميل (وضع تجريبي معزول):"
                  : "Simulate a customer message (isolated demo):"}
              </p>
              <div className="example-list">
                {copy.examples.map((example) => (
                  <button
                    type="button"
                    key={example}
                    disabled={busy}
                    onClick={() => simulate(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="inbox-detail">
          {!selected && (
            <EmptyState
              title={
                language === "ar" ? "اختر محادثة" : "Select a conversation"
              }
              body={
                language === "ar"
                  ? "افتح محادثة من القائمة لعرض السجل الكامل والرد."
                  : "Open a conversation to view the complete timeline and reply."
              }
            />
          )}
          {selected && (
            <>
              <div className="detail-head">
                <div>
                  <h2 style={{ margin: 0 }}>
                    {selected.customer.display_name}
                  </h2>
                  <p className="field-hint" style={{ margin: 0 }}>
                    {channelLabels[selected.channel_type]?.[language] ??
                      selected.channel_type}
                    {selected.customer.phone
                      ? ` · ${selected.customer.phone}`
                      : ""}{" "}
                    · {copy.leadScore} {selected.customer.lead_score}
                  </p>
                </div>
                <div className="actions">
                  {selected.status !== "resolved" ? (
                    <Button
                      variant="secondary"
                      onClick={() => setStatus("resolved")}
                      disabled={busy}
                    >
                      <IconCheck size={15} />
                      {language === "ar" ? "إنهاء" : "Resolve"}
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      onClick={() => setStatus("open")}
                      disabled={busy}
                    >
                      {language === "ar" ? "إعادة فتح" : "Reopen"}
                    </Button>
                  )}
                </div>
              </div>

              <div className="timeline" ref={timelineRef}>
                {selected.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`bubble ${message.direction === "inbound" ? "bubble--in" : message.sender_type === "note" ? "bubble--note" : "bubble--out"}`}
                  >
                    <p>{message.body}</p>
                    {message.attachments.map(
                      (attachment, index) =>
                        attachment.url &&
                        (attachment.type === "image" ? (
                          <img
                            className="message-media"
                            src={attachment.url}
                            alt={attachment.filename || copy.attachedImage}
                            key={`${attachment.url}-${index}`}
                          />
                        ) : attachment.type === "audio" ? (
                          <audio
                            className="message-audio"
                            src={attachment.url}
                            controls
                            key={`${attachment.url}-${index}`}
                          />
                        ) : (
                          <a
                            className="message-attachment"
                            href={attachment.url}
                            target="_blank"
                            rel="noreferrer"
                            key={`${attachment.url}-${index}`}
                          >
                            {attachment.filename || copy.openDocument}
                          </a>
                        )),
                    )}
                    <small>
                      {message.sender_type === "note"
                        ? `${copy.internalNote} · `
                        : ""}
                      {formatDateTime(message.created_at, language)}
                      {message.direction === "outbound" &&
                        message.sender_type !== "note" &&
                        ` · ${messageStatusLabel(message.status, language)}`}
                    </small>
                  </div>
                ))}
              </div>

              {suggestion && suggestion.recommendations.length > 0 && (
                <div
                  className="suggest-strip"
                  aria-label={copy.suggestedProducts}
                >
                  {suggestion.recommendations.map((recommendation) => (
                    <span className="badge" key={recommendation.product_id}>
                      {recommendation.product.name} —{" "}
                      {recommendation.product.price} {copy.currency}
                    </span>
                  ))}
                </div>
              )}

              {suggestion && (
                <SuggestionEvidence
                  suggestion={suggestion}
                  language={language}
                />
              )}

              <div className="reply-area">
                <textarea
                  rows={3}
                  value={reply}
                  maxLength={4000}
                  placeholder={
                    language === "ar" ? "اكتب ردك…" : "Write a reply…"
                  }
                  onChange={(event) => setReply(event.target.value)}
                  aria-label={language === "ar" ? "نص الرد" : "Reply text"}
                />
                <div className="actions">
                  {selected.channel_type === "whatsapp" && (
                    <label className="button button--secondary media-picker">
                      {copy.attachFile}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,application/pdf,text/plain,audio/*"
                        onChange={(event) =>
                          setMedia(event.target.files?.[0] ?? null)
                        }
                      />
                    </label>
                  )}
                  <Button variant="secondary" onClick={suggest} disabled={busy}>
                    <IconSpark size={16} />
                    {language === "ar" ? "اقتراح ذكي" : "Smart suggestion"}
                  </Button>
                  {media && (
                    <Button
                      variant="secondary"
                      onClick={sendMedia}
                      disabled={busy}
                    >
                      {copy.sendFile} {media.name}
                    </Button>
                  )}
                  <Button onClick={sendReply} disabled={busy || !reply.trim()}>
                    <IconSend size={16} />
                    {language === "ar" ? "إرسال" : "Send"}
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>

        <InboxContextRail
          fallbackCustomer={selected?.customer ?? null}
          customer={customerContext}
          orders={relatedOrders}
          loading={contextLoading}
          error={contextError}
          ordersUnavailable={ordersUnavailable}
          onRetry={() => {
            if (selected) void loadContext(selected);
          }}
          language={language}
        />
      </div>
    </>
  );
}
