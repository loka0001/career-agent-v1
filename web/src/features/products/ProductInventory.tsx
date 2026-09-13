import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Alert, Badge, Button, Card, Skeleton } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { formatCurrency, formatDateTime } from "../../lib/format";
import type {
  InventoryAdjustmentInput,
  InventoryTransaction,
  ProductRecord,
  ProductVariant,
} from "../../lib/types";
import { inventoryCopy } from "./inventoryCopy";

function readPending(key: string): InventoryAdjustmentInput | null {
  try {
    const value = JSON.parse(
      sessionStorage.getItem(key) ?? "null",
    ) as InventoryAdjustmentInput | null;
    return value &&
      typeof value.idempotency_key === "string" &&
      value.idempotency_key.startsWith("inventory-") &&
      typeof value.reason === "string" &&
      Number.isInteger(value.delta) &&
      typeof value.variant_id === "string"
      ? value
      : null;
  } catch {
    return null;
  }
}

function storePending(key: string, value: InventoryAdjustmentInput | null) {
  try {
    if (value) sessionStorage.setItem(key, JSON.stringify(value));
    else sessionStorage.removeItem(key);
  } catch {
    /* In-memory retry remains available when browser storage is disabled. */
  }
}

export function ProductInventory({
  product,
  language,
  canEdit,
  disabled,
  onBusy,
  onUpdated,
  onStockEditable,
}: {
  product: ProductRecord;
  language: "ar" | "en";
  canEdit: boolean;
  disabled: boolean;
  onBusy: (busy: boolean) => void;
  onUpdated: (product: ProductRecord) => void;
  onStockEditable?: (editable: boolean) => void;
}) {
  const copy = inventoryCopy(language);
  const storageKey = `commerce-inventory:v1:${product.store_id}:${product.product_id}`;
  const [pending] = useState(() => readPending(storageKey));
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [history, setHistory] = useState<InventoryTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedId, setSelectedId] = useState(pending?.variant_id ?? "");
  const [delta, setDelta] = useState(pending ? String(pending.delta) : "");
  const [reason, setReason] = useState(pending?.reason ?? "");
  const [uncertain, setUncertain] = useState(!!pending);
  const [adding, setAdding] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [options, setOptions] = useState<{ name: string; value: string }[]>([]);
  const requestRef = useRef<InventoryAdjustmentInput | null>(pending);
  const sequence = useRef(0);
  const mounted = useRef(true);
  const mutation = useRef(false);
  const local = product.source_of_truth !== "external";
  const selected =
    variants.find((variant) => variant.variant_id === selectedId) ??
    variants[0];
  const writable = canEdit && local && !disabled && !loading && !loadFailed;
  const id = product.product_id;
  const load = useCallback(async () => {
    const request = ++sequence.current;
    setLoading(true);
    setLoadFailed(false);
    try {
      const [nextVariants, nextHistory] = await Promise.all([
        api.productVariants(id),
        api.inventoryHistory(id),
      ]);
      if (!mounted.current || request !== sequence.current) return;
      setVariants(nextVariants);
      setHistory(nextHistory);
      onStockEditable?.(
        nextVariants.filter((variant) => variant.status === "active").length ===
          1,
      );
    } catch {
      if (mounted.current && request === sequence.current) setLoadFailed(true);
    } finally {
      if (mounted.current && request === sequence.current) setLoading(false);
    }
  }, [id, onStockEditable]);
  useEffect(() => {
    mounted.current = true;
    void load();
    return () => {
      mounted.current = false;
      ++sequence.current;
    };
  }, [load]);
  useEffect(() => {
    if (!busy && !uncertain) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [busy, uncertain]);

  async function adjust(event?: FormEvent) {
    event?.preventDefault();
    if (!writable || mutation.current || !selected) return;
    const amount = Number(delta);
    if (
      !uncertain &&
      (!Number.isInteger(amount) ||
        !amount ||
        Math.abs(amount) > 1000000 ||
        !reason.trim())
    ) {
      setError(copy.invalid);
      return;
    }
    const payload =
      uncertain && requestRef.current
        ? requestRef.current
        : {
            variant_id: selected.variant_id,
            delta: amount,
            reason: reason.trim(),
            reference_type: "manual",
            reference_id: "",
            allow_negative: false,
            idempotency_key: `inventory-${crypto.randomUUID()}`,
          };
    requestRef.current = payload;
    storePending(storageKey, payload);
    mutation.current = true;
    setBusy(true);
    onBusy(true);
    setError("");
    setNotice("");
    try {
      await api.adjustInventory(id, payload);
      storePending(storageKey, null);
      if (!mounted.current) return;
      requestRef.current = null;
      setUncertain(false);
      setDelta("");
      setReason("");
      setNotice(copy.saved);
      const fresh = await api.product(id);
      if (mounted.current) onUpdated(fresh);
      await load();
    } catch (failure) {
      if (!mounted.current) return;
      // If the mutation already succeeded, a failed refresh must never repeat it.
      if (!requestRef.current) {
        setLoadFailed(true);
        setError(copy.loadError);
      } else {
        const ambiguous =
          !(failure instanceof ApiError) || failure.status >= 500;
        setUncertain(ambiguous);
        setError(
          ambiguous
            ? copy.uncertain
            : `${copy.failed}${failure instanceof ApiError ? ` (${failure.body.code})` : ""}`,
        );
        if (!ambiguous) {
          requestRef.current = null;
          storePending(storageKey, null);
        }
      }
    } finally {
      mutation.current = false;
      if (mounted.current) {
        setBusy(false);
        onBusy(false);
      }
    }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!writable || mutation.current || uncertain) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const entries = options.map((option) => [
      option.name.trim(),
      option.value.trim(),
    ]);
    if (
      entries.some(([key, value]) => !key || !value) ||
      new Set(entries.map(([key]) => key)).size !== entries.length
    ) {
      setError(copy.optionsInvalid);
      return;
    }
    mutation.current = true;
    setBusy(true);
    onBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await api.createProductVariant(id, {
        variant_id: String(data.get("variantId")),
        title: String(data.get("title")).trim(),
        sku: String(data.get("sku")).trim(),
        price: String(data.get("price")),
        stock: Number(data.get("stock")),
        stock_policy:
          data.get("stock_policy") === "continue" ? "continue" : "deny",
        options: Object.fromEntries(entries),
      });
      if (!mounted.current) return;
      setAdding(false);
      setOptions([]);
      setSelectedId(created.variant_id);
      setNotice(copy.created);
      const fresh = await api.product(id);
      if (mounted.current) onUpdated(fresh);
      await load();
    } catch (failure) {
      if (mounted.current)
        setError(
          `${copy.createFailed}${failure instanceof ApiError ? ` (${failure.body.code})` : ""}`,
        );
    } finally {
      mutation.current = false;
      if (mounted.current) {
        setBusy(false);
        onBusy(false);
      }
    }
  }

  return (
    <Card className="product-inventory" aria-label={copy.title}>
      <div className="row-between">
        <h2>{copy.title}</h2>
        <Button
          variant="secondary"
          disabled={loading || busy}
          onClick={() => void load()}
        >
          {copy.refresh}
        </Button>
      </div>
      {!local ? <Alert>{copy.external}</Alert> : null}
      {disabled && canEdit && local ? (
        <p className="field-hint">{copy.editFirst}</p>
      ) : null}
      {loadFailed ? <Alert tone="error">{copy.loadError}</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
      {uncertain && !error ? (
        <Alert tone="warning">{copy.uncertain}</Alert>
      ) : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {loading ? (
        <Skeleton height="8rem" />
      ) : (
        <>
          <div className="variant-list">
            {variants.map((variant) => (
              <article className="variant-row" key={variant.variant_id}>
                <div>
                  <b>{variant.title}</b>
                  <small>
                    <bdi>{variant.sku}</bdi> · <bdi>{variant.variant_id}</bdi>
                  </small>
                  <small>
                    {Object.entries(variant.options)
                      .map(([key, value]) => `${key}: ${value}`)
                      .join(" · ")}
                  </small>
                </div>
                <div>
                  <small>{copy.price}</small>
                  <bdi>
                    {formatCurrency(variant.price, language, product.currency)}
                  </bdi>
                </div>
                <div>
                  <small>{copy.stock}</small>
                  <strong>{variant.stock}</strong>
                </div>
                <div>
                  <Badge
                    tone={variant.status === "active" ? "success" : "neutral"}
                  >
                    {variant.status === "active" ? copy.active : copy.inactive}
                  </Badge>
                  <small>
                    {variant.stock_policy === "continue"
                      ? copy.backorders
                      : copy.stopAtZero}
                  </small>
                </div>
              </article>
            ))}
          </div>
          {!variants.length && !loadFailed ? <p>{copy.empty}</p> : null}
          {canEdit && local ? (
            <>
              {variants.length ? (
                <form
                  onSubmit={(event) => void adjust(event)}
                  className="inventory-adjustment"
                >
                  <h3>{copy.adjust}</h3>
                  <fieldset
                    className="product-detail__fields form-grid"
                    disabled={!writable || busy || uncertain}
                  >
                    <label>
                      {copy.variant}
                      <select
                        value={selected?.variant_id ?? ""}
                        onChange={(event) => setSelectedId(event.target.value)}
                      >
                        {variants.map((variant) => (
                          <option
                            key={variant.variant_id}
                            value={variant.variant_id}
                          >
                            {variant.title} · {variant.sku}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      {copy.delta}
                      <input
                        type="number"
                        step="1"
                        min="-1000000"
                        max="1000000"
                        value={delta}
                        required
                        onChange={(event) => setDelta(event.target.value)}
                      />
                    </label>
                    <label className="full">
                      {copy.reason}
                      <input
                        value={reason}
                        maxLength={80}
                        required
                        onChange={(event) => setReason(event.target.value)}
                      />
                    </label>
                  </fieldset>
                  <p className="field-hint">{copy.deltaHint}</p>
                  {delta && selected && Number.isFinite(Number(delta)) ? (
                    <p>
                      {copy.projected}:{" "}
                      <strong>{selected.stock + Number(delta)}</strong>
                      <small className="field-hint"> {copy.previewHint}</small>
                    </p>
                  ) : null}
                  <Button type="submit" disabled={!writable || busy}>
                    {busy ? copy.busy : uncertain ? copy.retry : copy.adjust}
                  </Button>
                </form>
              ) : null}
              {!adding ? (
                <Button
                  variant="secondary"
                  disabled={!writable || busy || uncertain}
                  onClick={() => setAdding(true)}
                >
                  {copy.create}
                </Button>
              ) : (
                <form
                  onSubmit={(event) => void create(event)}
                  className="inventory-adjustment"
                >
                  <h3>{copy.create}</h3>
                  <p className="field-hint">{copy.createHint}</p>
                  <fieldset
                    className="product-detail__fields form-grid"
                    disabled={!writable || busy}
                  >
                    <label>
                      {copy.variantId}
                      <input
                        name="variantId"
                        pattern={"[A-Za-z0-9_\\-]+"}
                        maxLength={64}
                        required
                      />
                    </label>
                    <label>
                      {copy.newTitle}
                      <input name="title" maxLength={160} required />
                    </label>
                    <label>
                      {copy.sku}
                      <input name="sku" maxLength={100} required />
                    </label>
                    <label>
                      {copy.price} ({product.currency ?? "EGP"})
                      <input
                        name="price"
                        type="number"
                        min="0.01"
                        max="9999999999.99"
                        step="0.01"
                        required
                      />
                    </label>
                    <label>
                      {copy.initialStock}
                      <input
                        name="stock"
                        type="number"
                        min="0"
                        max="1000000"
                        step="1"
                        defaultValue="0"
                        required
                      />
                    </label>
                    <label>
                      {copy.stockPolicy}
                      <select name="stock_policy">
                        <option value="deny">{copy.stopAtZero}</option>
                        <option value="continue">{copy.backorders}</option>
                      </select>
                    </label>
                    {options.map((option, index) => (
                      <div className="full inventory-option" key={index}>
                        <label>
                          {copy.optionName} {index + 1}
                          <input
                            value={option.name}
                            required
                            onChange={(event) =>
                              setOptions((current) =>
                                current.map((item, key) =>
                                  key === index
                                    ? { ...item, name: event.target.value }
                                    : item,
                                ),
                              )
                            }
                          />
                        </label>
                        <label>
                          {copy.optionValue} {index + 1}
                          <input
                            value={option.value}
                            required
                            onChange={(event) =>
                              setOptions((current) =>
                                current.map((item, key) =>
                                  key === index
                                    ? { ...item, value: event.target.value }
                                    : item,
                                ),
                              )
                            }
                          />
                        </label>
                        <Button
                          type="button"
                          variant="ghost"
                          aria-label={`${copy.removeOption} ${index + 1}`}
                          onClick={() =>
                            setOptions((current) =>
                              current.filter((_, key) => key !== index),
                            )
                          }
                        >
                          {copy.removeOption}
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        setOptions((current) => [
                          ...current,
                          { name: "", value: "" },
                        ])
                      }
                    >
                      {copy.addOption}
                    </Button>
                  </fieldset>
                  <div className="actions">
                    <Button type="submit" disabled={!writable || busy}>
                      {busy ? copy.busy : copy.create}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => setAdding(false)}
                    >
                      {copy.cancel}
                    </Button>
                  </div>
                </form>
              )}
            </>
          ) : null}
          <section className="inventory-history">
            <h3>{copy.history}</h3>
            <p className="field-hint">{copy.historyHint}</p>
            {history.slice(0, expanded ? 100 : 5).map((entry) => (
              <article className="inventory-history__row" key={entry.id}>
                <div>
                  <b>{entry.reason}</b>
                  <small>
                    <bdi>{entry.variant_id ?? product.product_id}</bdi> ·{" "}
                    {formatDateTime(entry.created_at, language)}
                  </small>
                </div>
                <dl>
                  <div>
                    <dt>{copy.change}</dt>
                    <dd>
                      <bdi>
                        {entry.delta > 0 ? "+" : ""}
                        {entry.delta}
                      </bdi>
                    </dd>
                  </div>
                  <div>
                    <dt>{copy.before}</dt>
                    <dd>{entry.quantity_before}</dd>
                  </div>
                  <div>
                    <dt>{copy.after}</dt>
                    <dd>{entry.quantity_after}</dd>
                  </div>
                </dl>
              </article>
            ))}
            {!history.length && !loadFailed ? <p>{copy.noHistory}</p> : null}
            {history.length > 5 ? (
              <Button
                variant="ghost"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? copy.showLess : copy.showAll}
              </Button>
            ) : null}
          </section>
        </>
      )}
    </Card>
  );
}
