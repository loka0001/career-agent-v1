import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useAuth } from "../../app/AuthContext";
import {
  IconBox,
  IconDashboard,
  IconList,
  IconPlus,
} from "../../components/icons";
import { ProductCard } from "../../components/ProductCard";
import { Alert, Button, Card, EmptyState, Skeleton } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type { ProductRecord } from "../../lib/types";
import { formatCurrency } from "../../lib/format";
import { ProductDetail } from "./ProductDetail";
import { productStatusLabels } from "./productCopy";

type StockFilter = "all" | "available" | "low" | "out";
type ViewMode = "grid" | "table";

const stockFilters: { id: StockFilter; ar: string; en: string }[] = [
  { id: "all", ar: "الكل", en: "All" },
  { id: "available", ar: "متاح", en: "Available" },
  { id: "low", ar: "مخزون منخفض", en: "Low stock" },
  { id: "out", ar: "نفد", en: "Out" },
];

export function ProductsPage() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const canEdit = !!user && ["owner", "admin", "marketer"].includes(user.role);
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("product");
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const search = params.get("q") ?? "";
  const category = params.get("category") ?? "all";
  const stockFilter = (params.get("stock") ?? "all") as StockFilter;
  const viewMode: ViewMode = params.get("view") === "grid" ? "grid" : "table";
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  function filter(key: string, value: string) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (!value || value === "all") next.delete(key);
        else next.set(key, value);
        return next;
      },
      { replace: true },
    );
  }
  function productLink(id: string) {
    const next = new URLSearchParams(params);
    next.set("product", id);
    return `?${next}`;
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .products()
      .then((result) => {
        if (active) setProducts(result);
      })
      .catch(
        (reason) =>
          active &&
          setError(
            reason instanceof ApiError
              ? reason.message
              : language === "ar"
                ? "تعذر تحميل المنتجات"
                : "Products could not be loaded",
          ),
      )
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [language, retry]);

  const categories = useMemo(
    () =>
      [...new Set(products.map((product) => product.category))].sort((a, b) =>
        a.localeCompare(b),
      ),
    [products],
  );
  const visible = useMemo(
    () =>
      products.filter((product) => {
        if (
          !`${product.name} ${product.product_id} ${product.category}`
            .toLowerCase()
            .includes(search.trim().toLowerCase())
        )
          return false;
        if (category !== "all" && product.category !== category) return false;
        if (stockFilter === "available" && product.stock === 0) return false;
        if (stockFilter === "low" && (product.stock === 0 || product.stock > 5))
          return false;
        if (stockFilter === "out" && product.stock !== 0) return false;
        return true;
      }),
    [products, search, category, stockFilter],
  );

  const outOfStock = products.filter((product) => product.stock === 0).length;

  if (selectedId)
    return (
      <ProductDetail
        key={selectedId}
        id={selectedId}
        language={language}
        canEdit={canEdit}
        onBack={() => {
          setParams((current) => {
            const next = new URLSearchParams(current);
            next.delete("product");
            return next;
          });
          setRetry((value) => value + 1);
        }}
        onUpdated={(updated) =>
          setProducts((current) =>
            current.map((item) =>
              item.product_id === updated.product_id ? updated : item,
            ),
          )
        }
      />
    );

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            <IconBox size={14} /> {language === "ar" ? "الكتالوج" : "Catalog"}
          </span>
          <h1>{language === "ar" ? "المنتجات" : "Products"}</h1>
          <p>
            {language === "ar"
              ? `${products.length} منتجًا — منها ${outOfStock} نفد مخزونه.`
              : `${products.length} products — ${outOfStock} out of stock.`}
          </p>
        </div>
        {canEdit ? (
          <Link className="button button--primary" to="/app/products/new">
            <IconPlus size={17} />
            {language === "ar" ? "إضافة منتج" : "Add product"}
          </Link>
        ) : null}
      </div>

      <Card className="filter-bar">
        <label className="search-label">
          {language === "ar" ? "بحث" : "Search"}
          <input
            type="search"
            value={search}
            onChange={(event) => filter("q", event.target.value)}
            placeholder={
              language === "ar"
                ? "الاسم أو المعرّف أو الفئة"
                : "Name, ID, or category"
            }
          />
        </label>
        <label>
          {language === "ar" ? "الفئة" : "Category"}
          <select
            value={category}
            onChange={(event) => filter("category", event.target.value)}
          >
            <option value="all">
              {language === "ar" ? "كل الفئات" : "All categories"}
            </option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <div
          className="chip-row"
          role="group"
          aria-label={
            language === "ar" ? "تصفية حسب المخزون" : "Filter by stock"
          }
        >
          {stockFilters.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`chip ${stockFilter === item.id ? "active" : ""}`}
              aria-pressed={stockFilter === item.id}
              onClick={() => filter("stock", item.id)}
            >
              {item[language]}
            </button>
          ))}
        </div>
        <div
          className="segmented-control product-view-toggle"
          role="group"
          aria-label={language === "ar" ? "طريقة العرض" : "View mode"}
        >
          <button
            type="button"
            className={viewMode === "grid" ? "active" : ""}
            aria-pressed={viewMode === "grid"}
            onClick={() => filter("view", "grid")}
          >
            <IconDashboard size={16} /> {language === "ar" ? "شبكة" : "Grid"}
          </button>
          <button
            type="button"
            className={viewMode === "table" ? "active" : ""}
            aria-pressed={viewMode === "table"}
            onClick={() => filter("view", "table")}
          >
            <IconList size={16} /> {language === "ar" ? "جدول" : "Table"}
          </button>
        </div>
      </Card>
      {!loading && !error ? (
        <p role="status" className="field-hint">
          {language === "ar"
            ? `عرض ${visible.length} من ${products.length}`
            : `Showing ${visible.length} of ${products.length}`}
        </p>
      ) : null}

      {loading && (
        <div className="product-grid">
          {[1, 2, 3, 4, 5, 6].map((key) => (
            <Card key={key}>
              <Skeleton height="12rem" />
            </Card>
          ))}
        </div>
      )}
      {error && (
        <Alert tone="error">
          <div>
            <p>{error}</p>
            <Button
              variant="secondary"
              onClick={() => setRetry((value) => value + 1)}
            >
              {language === "ar" ? "إعادة المحاولة" : "Retry"}
            </Button>
          </div>
        </Alert>
      )}
      {!loading && !error && visible.length === 0 && (
        <EmptyState
          title={language === "ar" ? "لا توجد نتائج" : "No results"}
          body={
            language === "ar"
              ? "غيّر كلمة البحث أو الفلاتر، أو أضف أول منتج."
              : "Change the search or filters, or add the first product."
          }
          action={
            search || category !== "all" || stockFilter !== "all" ? (
              <Button onClick={() => setParams({})}>
                {language === "ar" ? "مسح الفلاتر" : "Clear filters"}
              </Button>
            ) : canEdit ? (
              <Link className="button button--primary" to="/app/products/new">
                {language === "ar" ? "إضافة منتج" : "Add product"}
              </Link>
            ) : undefined
          }
        />
      )}
      {!loading &&
        !error &&
        visible.length > 0 &&
        (viewMode === "grid" ? (
          <div className="product-grid">
            {visible.map((product) => (
              <ProductCard
                product={product}
                language={language}
                key={product.product_id}
                detailHref={productLink(product.product_id)}
              />
            ))}
          </div>
        ) : (
          <Card className="product-table-wrap">
            <div
              className="product-table"
              role="table"
              aria-label={
                language === "ar" ? "جدول المنتجات" : "Products table"
              }
            >
              <div className="product-table-row product-table-head" role="row">
                {[
                  language === "ar" ? "المنتج" : "Product",
                  language === "ar" ? "الفئة" : "Category",
                  language === "ar" ? "السعر" : "Price",
                  language === "ar" ? "المخزون" : "Stock",
                  language === "ar" ? "الحالة" : "Status",
                ].map((label) => (
                  <span role="columnheader" key={label}>
                    {label}
                  </span>
                ))}
              </div>
              {visible.map((product) => (
                <div
                  className="product-table-row"
                  role="row"
                  key={product.product_id}
                >
                  <span className="product-table-name" role="cell">
                    <img
                      src={
                        product.public_image_url ?? product.original_image_url
                      }
                      alt=""
                      width="44"
                      height="44"
                      loading="lazy"
                    />
                    <span>
                      <Link to={productLink(product.product_id)}>
                        <b>{product.name}</b>
                      </Link>
                      <small>{product.product_id}</small>
                    </span>
                  </span>
                  <span
                    role="cell"
                    data-label={language === "ar" ? "الفئة" : "Category"}
                  >
                    {product.category}
                  </span>
                  <span
                    role="cell"
                    data-label={language === "ar" ? "السعر" : "Price"}
                  >
                    {formatCurrency(product.price, language, product.currency)}
                  </span>
                  <span
                    role="cell"
                    data-label={language === "ar" ? "المخزون" : "Stock"}
                  >
                    {product.stock}
                  </span>
                  <span
                    role="cell"
                    data-label={language === "ar" ? "الحالة" : "Status"}
                  >
                    <span
                      className={`status-dot status-dot--${product.status === "active" ? "success" : "warning"}`}
                    />
                    {productStatusLabels[product.status][language]}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        ))}
    </>
  );
}
