import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { IconPlus, IconReceipt, IconRefresh } from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
} from "../../components/operations";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
} from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { formatDateTime, formatMoney } from "../../lib/format";
import type {
  ConversationSummary,
  OrderRecord,
  OrderStatus,
  ProductRecord,
} from "../../lib/types";

const nextStatus: Partial<Record<OrderStatus, OrderStatus>> = {
  draft: "pending",
  pending: "confirmed",
  confirmed: "paid",
  paid: "processing",
  processing: "shipped",
  shipped: "delivered",
};

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

const paymentStatusLabels: Record<string, { ar: string; en: string }> = {
  unpaid: { ar: "غير محصل", en: "Unpaid" },
  awaiting_cash: {
    ar: "بانتظار الدفع عند الاستلام",
    en: "Awaiting cash on delivery",
  },
  pending: { ar: "قيد التحصيل", en: "Pending" },
  paid: { ar: "تم التحصيل", en: "Paid" },
  cancelled: { ar: "ملغي", en: "Cancelled" },
  refunded: { ar: "مسترد", en: "Refunded" },
};

interface DraftLine {
  id: string;
  product_id: string;
  quantity: number;
}

function blankLine(productId = ""): DraftLine {
  return { id: crypto.randomUUID(), product_id: productId, quantity: 1 };
}

export function OrdersPage() {
  const { language } = useLanguage();
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [checkout, setCheckout] = useState<{
    orderId: number;
    url: string;
    provider: string;
  } | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [conversationId, setConversationId] = useState(0);
  const [lines, setLines] = useState<DraftLine[]>([blankLine()]);
  const [discount, setDiscount] = useState("0");
  const [shippingTotal, setShippingTotal] = useState("0");
  const [taxTotal, setTaxTotal] = useState("0");
  const [notes, setNotes] = useState("");
  const [shippingAddress, setShippingAddress] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(() =>
    crypto.randomUUID(),
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [nextOrders, nextProducts, inbox] = await Promise.all([
        api.orders(),
        api.products(),
        api.conversations(),
      ]);
      setOrders(nextOrders);
      setProducts(nextProducts);
      setConversations(inbox.conversations);
      setSelectedId((current) => current ?? nextOrders[0]?.id ?? null);
      setConversationId(
        (current) => current || inbox.conversations[0]?.id || 0,
      );
      setLines((current) =>
        current[0]?.product_id || !nextProducts[0]
          ? current
          : [blankLine(nextProducts[0].product_id)],
      );
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const selected = orders.find((order) => order.id === selectedId) ?? null;
  const canCreate =
    conversations.length > 0 && products.some((product) => product.stock > 0);

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    const items = lines
      .filter((line) => line.product_id && line.quantity > 0)
      .map(({ product_id, quantity }) => ({ product_id, quantity }));
    if (!conversationId || !items.length) {
      setError(
        language === "ar"
          ? "اختر محادثة ومنتجًا واحدًا على الأقل."
          : "Select a conversation and at least one product.",
      );
      return;
    }
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const created = await api.createOrder({
        conversation_id: conversationId,
        items,
        discount,
        shipping_total: shippingTotal,
        tax_total: taxTotal,
        currency: "EGP",
        idempotency_key: idempotencyKey,
        shipping: shippingAddress ? { address: shippingAddress } : {},
        notes,
      });
      setShowCreate(false);
      setSelectedId(created.id);
      setIdempotencyKey(crypto.randomUUID());
      setNotice(
        language === "ar"
          ? `أُنشئ الطلب #${created.id} وحُجز المخزون مرة واحدة.`
          : `Order #${created.id} was created and inventory was reserved once.`,
      );
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function transition(status: OrderStatus) {
    if (!selected) return;
    setWorking(true);
    setError("");
    setCheckout(null);
    try {
      await api.transitionOrder(selected.id, status, true);
      setNotice(
        language === "ar"
          ? `انتقل الطلب إلى «${statusLabels[status].ar}».`
          : `Order moved to “${statusLabels[status].en}”.`,
      );
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function createCheckout() {
    if (!selected) return;
    setWorking(true);
    setError("");
    try {
      const result = await api.checkoutOrder(selected.id);
      setCheckout({
        orderId: selected.id,
        url: result.url,
        provider: result.provider,
      });
      if (result.provider === "cod") await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  function cancelOrder() {
    if (
      window.confirm(
        language === "ar"
          ? "إلغاء الطلب وإعادة المخزون المحجوز؟"
          : "Cancel this order and restore reserved inventory?",
      )
    ) {
      void transition("cancelled");
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "الطلبات" : "Orders"}
        description={
          language === "ar"
            ? "أنشئ الطلب من محادثة حقيقية، ثم تابع المخزون والتحصيل والتنفيذ."
            : "Create an order from a real conversation, then track inventory, collection, and fulfillment."
        }
        action={
          <div className="actions">
            <Button variant="secondary" onClick={load}>
              <IconRefresh size={17} />
              {language === "ar" ? "تحديث" : "Refresh"}
            </Button>
            <Button onClick={() => setShowCreate((current) => !current)}>
              <IconPlus size={17} />
              {language === "ar" ? "طلب جديد" : "New order"}
            </Button>
          </div>
        }
      />
      {error ? <Alert tone="error">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      {showCreate ? (
        <Card className="order-create-panel">
          <div className="panel-head">
            <div>
              <h2>{language === "ar" ? "إنشاء طلب" : "Create order"}</h2>
              <p>
                {language === "ar"
                  ? "السعر والإجمالي وحجز المخزون تُحسب وتُتحقق في الخادم."
                  : "Pricing, totals, and inventory reservation are verified by the server."}
              </p>
            </div>
          </div>
          {!canCreate ? (
            <Alert tone="warning">
              {language === "ar"
                ? "تحتاج محادثة واردة ومنتجًا متاحًا في المخزون قبل إنشاء الطلب."
                : "An inbox conversation and an in-stock product are required."}{" "}
              <Link to="/app/inbox">
                {language === "ar" ? "افتح الرسائل" : "Open inbox"}
              </Link>
            </Alert>
          ) : (
            <form onSubmit={createOrder}>
              <label>
                {language === "ar" ? "محادثة العميل" : "Customer conversation"}
                <select
                  value={conversationId}
                  onChange={(event) =>
                    setConversationId(Number(event.target.value))
                  }
                  required
                >
                  {conversations.map((conversation) => (
                    <option value={conversation.id} key={conversation.id}>
                      {conversation.customer.display_name} · #{conversation.id}{" "}
                      · {conversation.channel_type}
                    </option>
                  ))}
                </select>
              </label>

              <fieldset className="order-lines-fieldset">
                <legend>
                  {language === "ar" ? "بنود الطلب" : "Order items"}
                </legend>
                {lines.map((line, index) => (
                  <div className="order-draft-line" key={line.id}>
                    <label>
                      {language === "ar" ? "المنتج" : "Product"}
                      <select
                        value={line.product_id}
                        onChange={(event) =>
                          setLines((current) =>
                            current.map((item) =>
                              item.id === line.id
                                ? { ...item, product_id: event.target.value }
                                : item,
                            ),
                          )
                        }
                        required
                      >
                        <option value="">
                          {language === "ar"
                            ? "اختر منتجًا"
                            : "Select a product"}
                        </option>
                        {products.map((product) => (
                          <option
                            value={product.product_id}
                            key={product.product_id}
                            disabled={product.stock < 1}
                          >
                            {product.name} ·{" "}
                            {formatMoney(product.price, language)} ·{" "}
                            {language === "ar" ? "متاح" : "stock"}{" "}
                            {product.stock}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      {language === "ar" ? "الكمية" : "Quantity"}
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={line.quantity}
                        onChange={(event) =>
                          setLines((current) =>
                            current.map((item) =>
                              item.id === line.id
                                ? {
                                    ...item,
                                    quantity: Number(event.target.value),
                                  }
                                : item,
                            ),
                          )
                        }
                        required
                      />
                    </label>
                    {lines.length > 1 ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() =>
                          setLines((current) =>
                            current.filter((item) => item.id !== line.id),
                          )
                        }
                        aria-label={
                          language === "ar"
                            ? `حذف البند ${index + 1}`
                            : `Remove item ${index + 1}`
                        }
                      >
                        {language === "ar" ? "حذف" : "Remove"}
                      </Button>
                    ) : null}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    setLines((current) => [...current, blankLine()])
                  }
                >
                  <IconPlus size={16} />
                  {language === "ar" ? "إضافة بند" : "Add item"}
                </Button>
              </fieldset>

              <div className="form-grid order-adjustments">
                <label>
                  {language === "ar" ? "الخصم" : "Discount"}
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={discount}
                    onChange={(event) => setDiscount(event.target.value)}
                  />
                </label>
                <label>
                  {language === "ar" ? "الشحن" : "Shipping"}
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={shippingTotal}
                    onChange={(event) => setShippingTotal(event.target.value)}
                  />
                </label>
                <label>
                  {language === "ar" ? "الضريبة" : "Tax"}
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={taxTotal}
                    onChange={(event) => setTaxTotal(event.target.value)}
                  />
                </label>
                <label className="full">
                  {language === "ar" ? "عنوان التوصيل" : "Delivery address"}
                  <input
                    value={shippingAddress}
                    onChange={(event) => setShippingAddress(event.target.value)}
                    maxLength={500}
                  />
                </label>
                <label className="full">
                  {language === "ar" ? "ملاحظات داخلية" : "Internal notes"}
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    maxLength={2000}
                  />
                </label>
              </div>
              <div className="actions">
                <Button type="submit" disabled={working}>
                  {working
                    ? language === "ar"
                      ? "جارٍ الإنشاء…"
                      : "Creating…"
                    : language === "ar"
                      ? "إنشاء وحجز المخزون"
                      : "Create and reserve inventory"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowCreate(false)}
                >
                  {language === "ar" ? "إلغاء" : "Cancel"}
                </Button>
              </div>
            </form>
          )}
        </Card>
      ) : null}

      {loading ? (
        <Spinner
          label={language === "ar" ? "جارٍ تحميل الطلبات…" : "Loading orders…"}
        />
      ) : orders.length === 0 ? (
        <EmptyState
          title={language === "ar" ? "لا توجد طلبات بعد" : "No orders yet"}
          body={
            language === "ar"
              ? "أنشئ أول طلب من محادثة عميل؛ لن تعرض هذه الصفحة أرقامًا أو طلبات افتراضية."
              : "Create the first order from a customer conversation; this page never invents order data."
          }
          action={
            <Button disabled={!canCreate} onClick={() => setShowCreate(true)}>
              {language === "ar" ? "إنشاء أول طلب" : "Create first order"}
            </Button>
          }
        />
      ) : (
        <div className="orders-layout">
          <Card className="orders-table-wrap">
            <div className="data-table" role="table" aria-label="Orders">
              <div className="data-row data-head" role="row">
                <span>{language === "ar" ? "الطلب" : "Order"}</span>
                <span>{language === "ar" ? "الحالة" : "Status"}</span>
                <span>{language === "ar" ? "القيمة" : "Value"}</span>
                <span>{language === "ar" ? "التاريخ" : "Date"}</span>
              </div>
              {orders.map((order) => (
                <button
                  type="button"
                  className={`data-row ${order.id === selectedId ? "selected" : ""}`}
                  key={order.id}
                  onClick={() => {
                    setSelectedId(order.id);
                    setCheckout(null);
                  }}
                >
                  <span>
                    <IconReceipt size={16} /> #{order.id}
                  </span>
                  <span>
                    <Badge
                      tone={
                        order.status === "delivered"
                          ? "success"
                          : order.status === "cancelled"
                            ? "error"
                            : "warning"
                      }
                    >
                      {statusLabels[order.status][language]}
                    </Badge>
                  </span>
                  <b>{formatMoney(order.total, language)}</b>
                  <small>{formatDateTime(order.created_at, language)}</small>
                </button>
              ))}
            </div>
          </Card>

          {selected ? (
            <div className="order-detail">
              <Card>
                <div className="panel-head">
                  <div>
                    <small>
                      {language === "ar" ? "طلب" : "Order"} #{selected.id}
                    </small>
                    <h2>{formatMoney(selected.total, language)}</h2>
                  </div>
                  <Badge>{statusLabels[selected.status][language]}</Badge>
                </div>
                <div className="order-items">
                  {selected.items.map((item, index) => (
                    <div
                      className="order-line"
                      key={`${item.product_id}-${item.variant_id ?? "base"}-${index}`}
                    >
                      <span className="grow">
                        <b>{item.product_name}</b>
                        <small>
                          {item.quantity} ×{" "}
                          {formatMoney(item.unit_price, language)}
                        </small>
                      </span>
                      <b>{formatMoney(item.line_total, language)}</b>
                    </div>
                  ))}
                </div>
                <dl className="totals">
                  <div>
                    <dt>
                      {language === "ar" ? "الإجمالي الفرعي" : "Subtotal"}
                    </dt>
                    <dd>{formatMoney(selected.subtotal, language)}</dd>
                  </div>
                  <div>
                    <dt>{language === "ar" ? "الخصم" : "Discount"}</dt>
                    <dd>{formatMoney(selected.discount, language)}</dd>
                  </div>
                  <div>
                    <dt>{language === "ar" ? "الشحن" : "Shipping"}</dt>
                    <dd>{formatMoney(selected.shipping_total, language)}</dd>
                  </div>
                  <div>
                    <dt>{language === "ar" ? "الضريبة" : "Tax"}</dt>
                    <dd>{formatMoney(selected.tax_total, language)}</dd>
                  </div>
                  <div>
                    <dt>{language === "ar" ? "الإجمالي" : "Total"}</dt>
                    <dd>{formatMoney(selected.total, language)}</dd>
                  </div>
                  <div>
                    <dt>
                      {language === "ar" ? "وسيلة التحصيل" : "Collection"}
                    </dt>
                    <dd>
                      {selected.payment_provider === "cod"
                        ? language === "ar"
                          ? "الدفع عند الاستلام"
                          : "Cash on delivery"
                        : selected.payment_provider ||
                          (language === "ar" ? "لم تُجهز" : "Not prepared")}
                    </dd>
                  </div>
                  <div>
                    <dt>
                      {language === "ar" ? "حالة التحصيل" : "Collection status"}
                    </dt>
                    <dd>
                      {(selected.payment_status
                        ? (paymentStatusLabels[selected.payment_status]?.[
                            language
                          ] ?? selected.payment_status)
                        : "") ||
                        (language === "ar" ? "لم يبدأ" : "Not started")}
                    </dd>
                  </div>
                  {Number(selected.refunded_amount) > 0 ? (
                    <div>
                      <dt>
                        {language === "ar" ? "المبلغ المسترد" : "Refunded"}
                      </dt>
                      <dd>{formatMoney(selected.refunded_amount, language)}</dd>
                    </div>
                  ) : null}
                </dl>
                <div className="actions">
                  {nextStatus[selected.status] ? (
                    <Button
                      disabled={working}
                      onClick={() => transition(nextStatus[selected.status]!)}
                    >
                      {language === "ar" ? "نقل إلى" : "Move to"}{" "}
                      {statusLabels[nextStatus[selected.status]!][language]}
                    </Button>
                  ) : null}
                  {["pending", "confirmed"].includes(selected.status) ? (
                    <Button
                      variant="secondary"
                      disabled={working}
                      onClick={createCheckout}
                    >
                      {language === "ar"
                        ? "تجهيز التحصيل"
                        : "Prepare collection"}
                    </Button>
                  ) : null}
                  {!["delivered", "cancelled", "refunded"].includes(
                    selected.status,
                  ) ? (
                    <Button
                      variant="ghost"
                      disabled={working}
                      onClick={cancelOrder}
                    >
                      {language === "ar" ? "إلغاء الطلب" : "Cancel order"}
                    </Button>
                  ) : null}
                </div>
                {checkout?.orderId === selected.id ? (
                  <Alert tone="success">
                    {checkout.provider === "cod" ? (
                      language === "ar" ? (
                        "تم تجهيز الطلب للدفع عند الاستلام، دون رابط أو بطاقة."
                      ) : (
                        "Cash on delivery is ready; no link or card is involved."
                      )
                    ) : (
                      <>
                        {language === "ar"
                          ? "رابط التحصيل الآمن جاهز."
                          : "Secure checkout is ready."}{" "}
                        <a href={checkout.url} target="_blank" rel="noreferrer">
                          {language === "ar"
                            ? "فتح صفحة التحصيل"
                            : "Open checkout"}
                        </a>
                      </>
                    )}
                  </Alert>
                ) : null}
              </Card>
              <Card>
                <h2>
                  {language === "ar" ? "خط حالة الطلب" : "Order timeline"}
                </h2>
                <div className="timeline compact-timeline">
                  {selected.timeline.map((entry, index) => (
                    <div
                      className="timeline-item"
                      key={`${entry.created_at}-${index}`}
                    >
                      <span className="timeline-dot" />
                      <div>
                        <b>
                          {entry.from_status
                            ? statusLabels[entry.from_status][language]
                            : language === "ar"
                              ? "إنشاء"
                              : "Created"}{" "}
                          → {statusLabels[entry.to_status][language]}
                        </b>
                        <p>
                          {entry.reason ||
                            (language === "ar"
                              ? "تحديث حالة"
                              : "Status update")}
                        </p>
                        <small>
                          {formatDateTime(entry.created_at, language)}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      )}
    </MotionPage>
  );
}
