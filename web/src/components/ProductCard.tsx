import type { ProductRecord } from "../lib/types";
import { Link } from "react-router";
import { formatCurrency } from "../lib/format";
import { Badge, Card } from "./ui";

const statusLabels: Record<
  ProductRecord["status"],
  { ar: string; en: string }
> = {
  draft: { ar: "مسودة", en: "Draft" },
  reviewed: { ar: "تمت المراجعة", en: "Reviewed" },
  active: { ar: "نشط", en: "Active" },
};

export function ProductCard({
  product,
  reasons,
  language = "ar",
  detailHref,
}: {
  product: ProductRecord;
  reasons?: string[];
  language?: "ar" | "en";
  detailHref?: string;
}) {
  const tone =
    product.stock === 0
      ? "error"
      : product.status === "active"
        ? "success"
        : "warning";
  return (
    <Card className="product-card" hover>
      <div className="thumb">
        <img
          src={product.public_image_url ?? product.original_image_url}
          alt={product.name}
          width="640"
          height="400"
          loading="lazy"
          decoding="async"
        />
        <Badge tone={tone}>{statusLabels[product.status][language]}</Badge>
      </div>
      <div className="body">
        <div className="row-between">
          <h3>
            {detailHref ? (
              <Link to={detailHref}>{product.name}</Link>
            ) : (
              product.name
            )}
          </h3>
        </div>
        <p className="price">
          {formatCurrency(product.price, language, product.currency)}
        </p>
        <p className="stock-line">
          <span
            className="dot"
            style={{
              color:
                product.stock === 0
                  ? "var(--danger)"
                  : product.stock <= 5
                    ? "var(--warning)"
                    : "var(--success)",
            }}
            aria-hidden="true"
          />
          {product.stock === 0
            ? language === "ar"
              ? "نفد المخزون"
              : "Out of stock"
            : language === "ar"
              ? `المخزون: ${product.stock}`
              : `Stock: ${product.stock}`}
        </p>
        {reasons && reasons.length > 0 && (
          <ul className="reason-list">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
