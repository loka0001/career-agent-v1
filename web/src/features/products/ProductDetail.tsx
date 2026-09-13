import { useEffect, useRef, useState, type FormEvent } from "react";
import { Alert, Badge, Button, Card, Skeleton } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { ProductRecord, ProductUpdateInput } from "../../lib/types";
import { productCopy, productStatusLabels } from "./productCopy";
import { ProductInventory } from "./ProductInventory";

function fields(product: ProductRecord) {
  return {
    name: product.name,
    category: product.category,
    description: product.description,
    features: product.features.join("\n"),
    benefits: product.customer_benefits.join("\n"),
    price: product.price,
    stock: String(product.stock),
  };
}

type Draft = ReturnType<typeof fields>;
const lines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

export function productReviewInput(
  product: ProductRecord,
  draft: Draft,
): ProductUpdateInput {
  const input: ProductUpdateInput = {
    name: draft.name.trim(),
    category: draft.category.trim(),
    description: draft.description.trim(),
    features: lines(draft.features),
    customer_benefits: lines(draft.benefits),
  };
  // Never send provider-owned fields, even unchanged. The backend enforces the same boundary.
  if (product.source_of_truth !== "external") {
    if (Number(draft.price) !== Number(product.price))
      input.price = draft.price;
    if (Number(draft.stock) !== product.stock)
      input.stock = Number(draft.stock);
  }
  return input;
}

export function ProductDetail({
  id,
  language,
  canEdit,
  onBack,
  onUpdated,
}: {
  id: string;
  language: "ar" | "en";
  canEdit: boolean;
  onBack: () => void;
  onUpdated: (product: ProductRecord) => void;
}) {
  const copy = productCopy(language);
  const [product, setProduct] = useState<ProductRecord | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState<"save" | "activate" | null>(null);
  const [inventoryBusy, setInventoryBusy] = useState(false);
  const [stockEditable, setStockEditable] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const mounted = useRef(true);
  const mutation = useRef(false);
  const dirty =
    !!product &&
    !!draft &&
    JSON.stringify(fields(product)) !== JSON.stringify(draft);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    api
      .product(id)
      .then((result) => {
        if (!active) return;
        setProduct(result);
        setDraft(fields(result));
      })
      .catch(() => {
        if (active) setLoadError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id, retry]);
  useEffect(() => {
    if (!dirty && !busy) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, busy]);

  async function mutate(action: "save" | "activate") {
    if (!product || !draft || !canEdit || mutation.current || inventoryBusy)
      return;
    if (action === "activate" && (dirty || product.status !== "reviewed"))
      return;
    if (lines(draft.features).length > 30 || lines(draft.benefits).length > 8) {
      setError(copy.required);
      return;
    }
    mutation.current = true;
    setBusy(action);
    setError("");
    setNotice("");
    try {
      const result =
        action === "save"
          ? await api.review(id, productReviewInput(product, draft))
          : await api.activate(id);
      if (!mounted.current) return;
      setProduct(result);
      setDraft(fields(result));
      onUpdated(result);
      setNotice(action === "save" ? copy.saved : copy.activated);
    } catch (reason) {
      if (mounted.current)
        setError(
          reason instanceof ApiError
            ? `${reason.message} (${reason.body.code})`
            : copy.actionFailed,
        );
    } finally {
      mutation.current = false;
      if (mounted.current) setBusy(null);
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    void mutate("save");
  }
  const change = (field: keyof Draft, value: string) => {
    setDraft((current) => (current ? { ...current, [field]: value } : null));
    setNotice("");
  };

  return (
    <div className="product-detail">
      <Button
        variant="ghost"
        disabled={!!busy || inventoryBusy}
        onClick={() => {
          if (!dirty || window.confirm(copy.discardConfirm)) onBack();
        }}
      >
        {copy.back}
      </Button>
      {loading ? (
        <Card>
          <Skeleton height="18rem" />
        </Card>
      ) : loadError || !product || !draft ? (
        <Alert tone="error">
          <div>
            <p>{copy.failed}</p>
            <Button
              variant="secondary"
              onClick={() => setRetry((value) => value + 1)}
            >
              {copy.retry}
            </Button>
          </div>
        </Alert>
      ) : (
        <>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {copy.details} · <bdi>{product.product_id}</bdi>
              </span>
              <h1>{product.name}</h1>
              <p>
                {copy.updated}: {formatDateTime(product.updated_at, language)}
              </p>
            </div>
            <Badge tone={product.status === "active" ? "success" : "warning"}>
              {productStatusLabels[product.status][language]}
            </Badge>
          </div>
          {error ? <Alert tone="error">{error}</Alert> : null}
          {notice ? <Alert tone="success">{notice}</Alert> : null}
          {!canEdit ? <Alert>{copy.readOnly}</Alert> : null}
          <form onSubmit={submit} className="product-detail__layout">
            <div className="product-detail__main">
              <Card>
                <h2>{copy.facts}</h2>
                <fieldset
                  disabled={!canEdit || !!busy || inventoryBusy}
                  className="product-detail__fields form-grid"
                >
                  <label>
                    {copy.name}
                    <input
                      value={draft.name}
                      maxLength={160}
                      required
                      onChange={(event) => change("name", event.target.value)}
                    />
                  </label>
                  <label>
                    {copy.category}
                    <input
                      value={draft.category}
                      maxLength={100}
                      required
                      onChange={(event) =>
                        change("category", event.target.value)
                      }
                    />
                  </label>
                  <label className="full">
                    {copy.description}
                    <textarea
                      value={draft.description}
                      maxLength={2000}
                      rows={5}
                      required
                      onChange={(event) =>
                        change("description", event.target.value)
                      }
                    />
                  </label>
                  <label className="full">
                    {copy.features}
                    <textarea
                      value={draft.features}
                      rows={5}
                      onChange={(event) =>
                        change("features", event.target.value)
                      }
                    />
                  </label>
                  <label className="full">
                    {copy.benefits}
                    <textarea
                      value={draft.benefits}
                      rows={4}
                      onChange={(event) =>
                        change("benefits", event.target.value)
                      }
                    />
                    <span className="field-hint">{copy.required}</span>
                  </label>
                </fieldset>
              </Card>
              <Card>
                <h2>{copy.commercial}</h2>
                {product.source_of_truth === "external" ? (
                  <Alert>{copy.external}</Alert>
                ) : null}
                <fieldset
                  className="product-detail__fields form-grid"
                  disabled={
                    !canEdit ||
                    !!busy ||
                    inventoryBusy ||
                    product.source_of_truth === "external"
                  }
                >
                  <label>
                    {copy.price} ({product.currency ?? "EGP"})
                    <input
                      type="number"
                      min="0.01"
                      max="9999999999.99"
                      step="0.01"
                      required
                      value={draft.price}
                      onChange={(event) => change("price", event.target.value)}
                    />
                  </label>
                  <label>
                    {copy.stock}
                    <input
                      type="number"
                      min={Math.min(0, product.stock)}
                      max={Math.max(1000000, product.stock)}
                      readOnly={product.stock < 0 || !stockEditable}
                      step="1"
                      required
                      value={draft.stock}
                      onChange={(event) => change("stock", event.target.value)}
                    />
                  </label>
                </fieldset>
                {product.source_of_truth !== "external" ? (
                  <p className="field-hint">
                    {stockEditable
                      ? copy.stockHint
                      : language === "en"
                        ? "Adjust stock per variant in Variants & inventory below."
                        : "عدّل مخزون كل خيار في قسم الخيارات والمخزون أدناه."}
                  </p>
                ) : null}
                <dl className="product-detail__metadata">
                  <div>
                    <dt>{copy.sku}</dt>
                    <dd>
                      <bdi>{product.sku || product.product_id}</bdi>
                    </dd>
                  </div>
                  <div>
                    <dt>{copy.source}</dt>
                    <dd>
                      {product.source_of_truth === "external"
                        ? (product.source_provider ?? "—")
                        : copy.local}
                    </dd>
                  </div>
                </dl>
              </Card>
            </div>
            <aside className="product-detail__aside">
              <Card>
                <img
                  className="product-detail__image"
                  src={product.public_image_url ?? product.original_image_url}
                  alt={product.name}
                  width="320"
                  height="240"
                />
                <h2>{copy.workflow}</h2>
                <p>{copy.reviewHint}</p>
                <p className="field-hint">{copy.activationHint}</p>
                {canEdit ? (
                  <div className="product-detail__actions">
                    {dirty ? <p role="status">{copy.dirty}</p> : null}
                    <Button
                      type="submit"
                      disabled={
                        !!busy ||
                        inventoryBusy ||
                        (!dirty && product.status !== "draft")
                      }
                    >
                      {busy === "save" ? copy.saving : copy.save}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={
                        !!busy ||
                        inventoryBusy ||
                        dirty ||
                        product.status !== "reviewed"
                      }
                      onClick={() => void mutate("activate")}
                    >
                      {busy === "activate" ? copy.activating : copy.activate}
                    </Button>
                    {dirty ? (
                      <Button
                        type="button"
                        variant="ghost"
                        disabled={!!busy || inventoryBusy}
                        onClick={() => {
                          if (window.confirm(copy.discardConfirm)) {
                            setDraft(fields(product));
                            setError("");
                            setNotice("");
                          }
                        }}
                      >
                        {copy.discard}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </Card>
            </aside>
          </form>
          <ProductInventory
            onStockEditable={setStockEditable}
            product={product}
            language={language}
            canEdit={canEdit}
            disabled={dirty || !!busy}
            onBusy={setInventoryBusy}
            onUpdated={(updated) => {
              setProduct(updated);
              setDraft(fields(updated));
              onUpdated(updated);
            }}
          />
        </>
      )}
    </div>
  );
}
