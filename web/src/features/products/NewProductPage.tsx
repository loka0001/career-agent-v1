import { useState, type FormEvent } from "react";
import { IconCheck, IconSpark } from "../../components/icons";
import { Alert, Button, Card, Spinner } from "../../components/ui";
import { PlatformPreview } from "../../components/PlatformPreview";
import { useLanguage } from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type {
  MarketingPack,
  ProductRecord,
  PublishResult,
} from "../../lib/types";
import { newProductCopy, type NewProductNotice } from "./newProductCopy";

export function NewProductPage() {
  const { language } = useLanguage();
  const copy = newProductCopy(language);
  const [step, setStep] = useState(0);
  const [product, setProduct] = useState<ProductRecord | null>(null);
  const [pack, setPack] = useState<MarketingPack | null>(null);
  const [results, setResults] = useState<PublishResult[]>([]);
  const [publishKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<NewProductNotice | null>(null);
  const [contentDirty, setContentDirty] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  function onboard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const features = String(form.get("features") ?? "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    form.delete("features");
    form.set("raw_features", JSON.stringify(features));
    void run(async () => {
      const created = await api.onboard(form);
      setProduct(created);
      setStep(1);
      setNotice("analysisReady");
    });
  }

  function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!product) return;
    const form = new FormData(event.currentTarget);
    void run(async () => {
      let updated = await api.review(product.product_id, {
        name: String(form.get("name")),
        category: String(form.get("category")),
        price: String(form.get("price")),
        stock: Number(form.get("stock")),
        features: String(form.get("features"))
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        customer_benefits: String(form.get("benefits"))
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        description: String(form.get("description")),
      });
      updated = await api.activate(updated.product_id);
      setProduct(updated);
      setStep(2);
      setNotice("activated");
    });
  }

  function generate() {
    if (!product) return;
    void run(async () => {
      const generated = await api.generatePack(product.product_id);
      setPack(generated);
      setContentDirty(false);
      setNotice("contentReady");
    });
  }
  function saveContent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pack) return;
    const form = new FormData(event.currentTarget);
    void run(async () => {
      const updated = await api.updatePack(pack.id, {
        facebook_message: String(form.get("facebook")),
        instagram_caption: String(form.get("instagram")),
        hashtags: String(form.get("hashtags")).split(/\s+/).filter(Boolean),
      });
      setPack(updated);
      setContentDirty(false);
      setNotice("contentSaved");
    });
  }
  function approve() {
    if (!pack || contentDirty) return;
    void run(async () => {
      const approved = await api.approvePack(pack.id);
      setPack(approved);
      setStep(3);
      setNotice("approved");
    });
  }
  function publish() {
    if (!pack || !window.confirm(copy.confirmPublish)) return;
    void run(async () => {
      const response = await api.publish(
        pack.id,
        ["facebook", "instagram"],
        publishKey,
      );
      setResults(response.results);
      setNotice("publishFinished");
    });
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            <IconSpark size={14} /> {copy.eyebrow}
          </span>
          <h1>{copy.title}</h1>
          <p>{copy.intro}</p>
        </div>
      </div>

      <ol className="stepper">
        {copy.steps.map((label, index) => (
          <li
            className={index === step ? "active" : index < step ? "done" : ""}
            key={label}
            aria-current={index === step ? "step" : undefined}
          >
            <span>{index < step ? <IconCheck size={14} /> : index + 1}</span>
            {label}
          </li>
        ))}
      </ol>

      {busy && (
        <div className="progress-banner">
          <Spinner label={copy.running} />
        </div>
      )}
      {error !== null && (
        <Alert tone="error">
          {error instanceof ApiError
            ? `${copy.requestFailed}: ${error.message} (${error.body.code})`
            : copy.unexpectedError}
        </Alert>
      )}
      {notice && (
        <Alert tone={notice === "publishFinished" ? "info" : "success"}>
          {copy[notice]}
        </Alert>
      )}

      {step === 0 && (
        <Card>
          <h2>{copy.dataTitle}</h2>
          <p style={{ color: "var(--muted)" }}>{copy.dataHint}</p>
          <form onSubmit={onboard} className="form-grid">
            <label>
              {copy.productId}
              <input
                name="product_id"
                pattern={"[A-Za-z0-9_\\-]+"}
                placeholder="P-1001"
                maxLength={64}
                required
              />
              <span className="field-hint">{copy.productIdHint}</span>
            </label>
            <label>
              {copy.name}
              <input name="name" maxLength={160} required />
            </label>
            <label>
              {copy.category}
              <select name="category" required>
                {Object.entries(copy.categories).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {copy.price}
              <input
                name="price"
                type="number"
                min="0.01"
                step="0.01"
                required
              />
            </label>
            <label>
              {copy.stock}
              <input
                name="stock"
                type="number"
                min="0"
                max="1000000"
                step="1"
                required
              />
            </label>
            <label className="full">
              {copy.rawFeatures}
              <textarea
                name="features"
                rows={5}
                placeholder={copy.featuresExample}
                required
              />
            </label>
            <label className="full file-input">
              {copy.image}
              <input
                name="image"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
              />
            </label>
            <div className="full">
              <Button type="submit" disabled={busy}>
                <IconSpark size={17} />
                {copy.analyze}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {step === 1 && product && (
        <Card>
          <h2>{copy.reviewTitle}</h2>
          <Alert>{copy.reviewHint}</Alert>
          <form onSubmit={review} className="form-grid">
            <label>
              {copy.name}
              <input
                name="name"
                maxLength={160}
                defaultValue={product.name}
                required
              />
            </label>
            <label>
              {copy.category}
              <input
                name="category"
                maxLength={100}
                defaultValue={product.category}
                required
              />
            </label>
            <label>
              {copy.price}
              <input
                name="price"
                type="number"
                step="0.01"
                min="0.01"
                defaultValue={product.price}
                required
              />
            </label>
            <label>
              {copy.stock}
              <input
                name="stock"
                type="number"
                min="0"
                max="1000000"
                step="1"
                defaultValue={product.stock}
                required
              />
            </label>
            <label className="full">
              {copy.features}
              <textarea
                name="features"
                rows={6}
                defaultValue={product.features.join("\n")}
              />
            </label>
            <label className="full">
              {copy.benefits}
              <textarea
                name="benefits"
                rows={4}
                defaultValue={product.customer_benefits.join("\n")}
              />
            </label>
            <label className="full">
              {copy.description}
              <textarea
                name="description"
                rows={5}
                defaultValue={product.description}
                maxLength={2000}
                required
              />
            </label>
            <div className="full">
              <Button type="submit" disabled={busy}>
                <IconCheck size={17} />
                {copy.activate}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {step === 2 && product && !pack && (
        <Card className="empty-state">
          <span className="feature-icon">
            <IconSpark size={21} />
          </span>
          <h2>{copy.contentTitle}</h2>
          <p>{copy.contentHint}</p>
          <Button onClick={generate} disabled={busy}>
            {copy.generate}
          </Button>
        </Card>
      )}

      {step === 2 && pack && (
        <>
          <div className="preview-grid">
            <PlatformPreview
              platform="Facebook"
              text={pack.facebook_message}
              imageUrl={pack.image_url}
            />
            <PlatformPreview
              platform="Instagram"
              text={pack.instagram_caption}
              imageUrl={pack.image_url}
            />
          </div>
          <Card>
            <h2>{copy.editTitle}</h2>
            {pack.validation_warnings.length > 0 && (
              <Alert tone="warning">
                <strong>{copy.validationWarnings}</strong>
                <p>
                  {pack.validation_warnings.join(
                    language === "ar" ? "، " : ", ",
                  )}
                </p>
              </Alert>
            )}
            <form onSubmit={saveContent} onChange={() => setContentDirty(true)}>
              <label>
                {copy.facebook}
                <textarea
                  name="facebook"
                  rows={8}
                  defaultValue={pack.facebook_message}
                  maxLength={4000}
                  required
                />
              </label>
              <label>
                {copy.instagram}
                <textarea
                  name="instagram"
                  rows={8}
                  defaultValue={pack.instagram_caption}
                  maxLength={2200}
                  required
                />
              </label>
              <label>
                {copy.hashtags}
                <input name="hashtags" defaultValue={pack.hashtags.join(" ")} />
              </label>
              <div className="actions">
                <Button type="submit" variant="secondary" disabled={busy}>
                  {copy.save}
                </Button>
                <Button
                  type="button"
                  onClick={approve}
                  disabled={
                    busy || contentDirty || pack.validation_warnings.length > 0
                  }
                >
                  <IconCheck size={17} />
                  {copy.approve}
                </Button>
              </div>
              <p className="field-hint">
                {contentDirty ? copy.unsavedHint : copy.approvalHint}
              </p>
            </form>
          </Card>
        </>
      )}

      {step === 3 && pack && (
        <Card>
          <h2>{copy.publishTitle}</h2>
          <p style={{ color: "var(--muted)" }}>
            {copy.approvalStatus}:{" "}
            <strong style={{ color: "var(--ink)" }}>
              {copy.statuses[pack.status]}
            </strong>
            . {copy.publishHint}
          </p>
          <Button onClick={publish} disabled={busy}>
            {copy.publish}
          </Button>
          {results.length > 0 && (
            <div className="result-grid" style={{ marginTop: "1rem" }}>
              {results.map((result) => (
                <Alert
                  key={result.platform}
                  tone={
                    result.success
                      ? result.raw_status === "DEMO"
                        ? "info"
                        : "success"
                      : "error"
                  }
                >
                  <div>
                    <strong>
                      {result.platform === "facebook"
                        ? "Facebook"
                        : "Instagram"}
                    </strong>
                    <p style={{ margin: "0.3rem 0 0" }}>
                      {result.success
                        ? result.raw_status === "DEMO"
                          ? copy.demo
                          : copy.success
                        : copy.failure}
                    </p>
                    {result.raw_status && (
                      <p>
                        {copy.providerStatus}: <code>{result.raw_status}</code>
                      </p>
                    )}
                    {!result.success && (
                      <p>
                        {copy.providerError}:{" "}
                        {result.error_code && (
                          <code>{result.error_code}: </code>
                        )}
                        {result.error_message ?? copy.noErrorDetails}
                      </p>
                    )}
                    {result.external_id && (
                      <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem" }}>
                        {copy.externalId}: <code>{result.external_id}</code>
                      </p>
                    )}
                    {result.permalink && (
                      <a
                        href={result.permalink}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {copy.openPost}
                      </a>
                    )}
                  </div>
                </Alert>
              ))}
            </div>
          )}
        </Card>
      )}
    </>
  );
}
