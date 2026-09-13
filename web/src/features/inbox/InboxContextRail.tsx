import { Link } from "react-router";
import { IconReceipt, IconUsers } from "../../components/icons";
import { Alert, Badge, Button, Card, Skeleton } from "../../components/ui";
import { formatCurrency } from "../../lib/format";
import type {
  CustomerIntelligence,
  CustomerSummary,
  OrderRecord,
  OrderStatus,
} from "../../lib/types";
import { inboxCopy } from "./inboxCopy";

const statusLabels: Record<OrderStatus, { ar: string; en: string }> = {
  draft: { ar: "مسودة", en: "Draft" },
  pending: { ar: "بانتظار التأكيد", en: "Pending" },
  confirmed: { ar: "مؤكد", en: "Confirmed" },
  paid: { ar: "تم التحصيل", en: "Collected" },
  processing: { ar: "قيد التجهيز", en: "Processing" },
  shipped: { ar: "تم الشحن", en: "Shipped" },
  delivered: { ar: "تم التسليم", en: "Delivered" },
  cancelled: { ar: "ملغي", en: "Cancelled" },
  refunded: { ar: "مسترد", en: "Refunded" },
};

function statusTone(status: OrderStatus) {
  if (status === "delivered" || status === "paid") return "success" as const;
  if (status === "cancelled" || status === "refunded") return "error" as const;
  if (status === "draft" || status === "pending") return "warning" as const;
  return "neutral" as const;
}

export function relatedOrdersForConversation(
  orders: OrderRecord[],
  customerId: number,
  conversationId: number,
) {
  return orders
    .filter(
      (order) =>
        order.conversation_id === conversationId ||
        order.customer_id === customerId,
    )
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() -
        new Date(left.updated_at).getTime(),
    );
}

export function InboxContextRail({
  fallbackCustomer,
  customer,
  orders,
  loading,
  error,
  language,
  ordersUnavailable = false,
  onRetry,
}: {
  fallbackCustomer: CustomerSummary | null;
  customer: CustomerIntelligence | null;
  orders: OrderRecord[];
  loading: boolean;
  error: string;
  language: "ar" | "en";
  ordersUnavailable?: boolean;
  onRetry?: () => void;
}) {
  const copy = inboxCopy(language);
  const profile = customer?.customer ?? fallbackCustomer;

  return (
    <Card className="inbox-context" aria-label={copy.contextTitle}>
      <div className="inbox-context__head">
        <span className="platform-mark" aria-hidden="true">
          <IconUsers size={19} />
        </span>
        <div>
          <small>{copy.customerProfile}</small>
          <h2>{copy.contextTitle}</h2>
        </div>
      </div>

      {loading ? (
        <div className="inbox-context__loading">
          <Skeleton height="4.4rem" />
          <Skeleton height="5.5rem" />
          <Skeleton height="7rem" />
        </div>
      ) : (
        <>
          {error ? (
            <Alert tone="warning">
              <div>
                <p>{error}</p>
                {onRetry ? (
                  <Button variant="secondary" onClick={onRetry}>
                    {copy.retryContext}
                  </Button>
                ) : null}
              </div>
            </Alert>
          ) : null}
          {!profile ? (
            <p className="empty-copy">{copy.selectForContext}</p>
          ) : null}
          {profile ? (
            <section className="inbox-context__profile">
              <div className="profile-head">
                <span className="avatar" aria-hidden="true">
                  {profile.display_name.slice(0, 1) || copy.avatarFallback}
                </span>
                <div className="grow">
                  <b>{profile.display_name}</b>
                  <small>{profile.phone ?? profile.email ?? "—"}</small>
                </div>
              </div>
              <div className="tag-list">
                {profile.tags.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
                {customer?.segments.map((segment) => (
                  <Badge key={segment} tone="success">
                    {(
                      {
                        new: { ar: "جديد", en: "New" },
                        vip: { ar: "مميز", en: "VIP" },
                        repeat: { ar: "عميل متكرر", en: "Repeat customer" },
                        "high-intent": {
                          ar: "نية شراء مرتفعة",
                          en: "High intent",
                        },
                        "abandoned-cart": {
                          ar: "سلة متروكة",
                          en: "Abandoned cart",
                        },
                        lapsed: { ar: "غير نشط", en: "Lapsed" },
                        "do-not-contact": {
                          ar: "عدم التواصل",
                          en: "Do not contact",
                        },
                      } as Record<string, { ar: string; en: string }>
                    )[segment]?.[language] ?? segment}
                  </Badge>
                ))}
              </div>
              <Link
                className="context-link"
                to={`/app/customers?customer=${profile.id}`}
              >
                {copy.viewCustomer}
              </Link>
            </section>
          ) : null}

          {customer ? (
            <dl className="inbox-context__metrics">
              <div>
                <dt>{copy.leadScore}</dt>
                <dd>{customer.lead_score}</dd>
              </div>
              <div>
                <dt>{copy.completedOrders}</dt>
                <dd>{customer.completed_orders}</dd>
              </div>
              <div>
                <dt>{copy.purchaseLikelihood}</dt>
                <dd>{Math.round(customer.purchase_probability)}%</dd>
              </div>
            </dl>
          ) : null}

          {profile ? (
            <section className="inbox-context__orders">
              <div className="inbox-context__section-head">
                <span>
                  <IconReceipt size={17} />
                  <b>{copy.recentOrders}</b>
                </span>
                <Link className="context-link" to="/app/orders">
                  {copy.viewOrders}
                </Link>
              </div>
              <p className="field-hint">{copy.recentHistoryHint}</p>
              {orders.length ? (
                <div className="context-order-list">
                  {orders.slice(0, 3).map((order) => (
                    <article className="context-order" key={order.id}>
                      <div>
                        <b>
                          {copy.order} #{order.id}
                        </b>
                        <Badge tone={statusTone(order.status)}>
                          {statusLabels[order.status][language]}
                        </Badge>
                      </div>
                      <small>
                        {order.items
                          .slice(0, 2)
                          .map((item) => item.product_name)
                          .join(" · ") || "—"}
                      </small>
                      <strong>
                        {formatCurrency(order.total, language, order.currency)}
                      </strong>
                    </article>
                  ))}
                </div>
              ) : ordersUnavailable ? null : (
                <p className="empty-copy">{copy.noRelatedOrders}</p>
              )}
            </section>
          ) : null}
        </>
      )}
    </Card>
  );
}
