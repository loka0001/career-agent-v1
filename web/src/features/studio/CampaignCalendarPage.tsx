import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  IconCalendar,
  IconCaretLeft,
  IconCaretRight,
  IconPlus,
} from "../../components/icons";
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
import type { ContentItem } from "../../lib/types";
import { contentStatusPresentation } from "./contentStatus";

type CalendarView = "month" | "week" | "agenda";

function keyFor(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfWeek(date: Date) {
  const result = new Date(date);
  result.setHours(12, 0, 0, 0);
  result.setDate(result.getDate() - result.getDay());
  return result;
}
function parseDate(value: string | null, fallback: Date) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return fallback;
  const date = new Date(`${value}T12:00:00`);
  return Number.isFinite(date.getTime()) && keyFor(date) === value
    ? date
    : fallback;
}
export function moveCalendarDate(
  date: Date,
  view: CalendarView,
  amount: number,
) {
  if (view === "month")
    return new Date(date.getFullYear(), date.getMonth() + amount, 1, 12);
  const next = new Date(date);
  next.setDate(next.getDate() + amount * 7);
  return next;
}

function CalendarItem({
  item,
  language,
}: {
  item: ContentItem;
  language: "ar" | "en";
}) {
  const status = contentStatusPresentation(item.status, language);
  return (
    <article className="calendar-item">
      <span className={`channel-stripe ${item.platform}`} />
      <span className="grow">
        <b>
          <Link to={`/app/studio?content=${item.id}`}>{item.title}</Link>
        </b>
        <small>
          {item.platform} ·{" "}
          {new Date(item.scheduled_for!).toLocaleTimeString(
            language === "ar" ? "ar-EG" : "en-US",
            { hour: "2-digit", minute: "2-digit" },
          )}
        </small>
      </span>
      <Badge tone={status.tone}>{status.label}</Badge>
    </article>
  );
}

export function CampaignCalendarPage() {
  const { language } = useLanguage();
  const [items, setItems] = useState<ContentItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [defaultView] = useState<CalendarView>(() =>
    window.matchMedia("(max-width: 767px)").matches ? "agenda" : "month",
  );
  const [initialDate] = useState(() => new Date());
  const [params, setParams] = useSearchParams();
  const requestedView = params.get("view");
  const view: CalendarView =
    requestedView === "month" ||
    requestedView === "week" ||
    requestedView === "agenda"
      ? requestedView
      : defaultView;
  const cursor = useMemo(
    () => parseDate(params.get("date"), initialDate),
    [params, initialDate],
  );
  const platform = params.get("platform") ?? "all";
  const [retry, setRetry] = useState(0);
  function update(key: string, value: string) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value === "all") next.delete(key);
      else next.set(key, value);
      return next;
    });
  }
  const setView = (value: CalendarView) => update("view", value);
  const setCursor = (date: Date) => update("date", keyFor(date));

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .studioContent()
      .then((next) => {
        if (active) setItems(next);
      })
      .catch((reason) => {
        if (active) setError(errorText(reason, language));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [retry, language]);

  const scheduledItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.scheduled_for &&
          Number.isFinite(new Date(item.scheduled_for).getTime()) &&
          (platform === "all" || item.platform === platform),
      ),
    [items, platform],
  );
  const days = useMemo(() => {
    const result = new Map<string, ContentItem[]>();
    [...scheduledItems]
      .sort(
        (a, b) =>
          new Date(a.scheduled_for!).getTime() -
          new Date(b.scheduled_for!).getTime(),
      )
      .forEach((item) => {
        const key = keyFor(new Date(item.scheduled_for!));
        result.set(key, [...(result.get(key) ?? []), item]);
      });
    return result;
  }, [scheduledItems]);
  const monthCells = useMemo(() => {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1, 12);
    const start = startOfWeek(first);
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return date;
    });
  }, [cursor]);
  const weekCells = useMemo(() => {
    const start = startOfWeek(cursor);
    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return date;
    });
  }, [cursor]);
  const agendaDays = useMemo(
    () =>
      [...days.entries()]
        .filter(
          ([day]) =>
            day >= keyFor(weekCells[0]!) && day <= keyFor(weekCells[6]!),
        )
        .sort(([a], [b]) => a.localeCompare(b)),
    [days, weekCells],
  );
  const platforms = [...new Set(items.map((item) => item.platform))];

  const move = (amount: number) => {
    setCursor(moveCalendarDate(cursor, view, amount));
  };

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "تقويم الحملات" : "Campaign calendar"}
        description={
          language === "ar"
            ? "خطّط المحتوى عبر المنصات وتابع حالة كل موعد."
            : "Plan content across platforms and follow every scheduled state."
        }
        action={
          <Link
            className="button button--primary"
            to="/app/studio?tab=campaign"
          >
            <IconPlus size={17} />
            {language === "ar" ? "حملة جديدة" : "New campaign"}
          </Link>
        }
      />
      {error ? (
        <Alert tone="error">
          {error}{" "}
          <Button
            variant="secondary"
            onClick={() => setRetry((value) => value + 1)}
          >
            {language === "ar" ? "إعادة المحاولة" : "Retry calendar"}
          </Button>
        </Alert>
      ) : null}
      <p className="field-hint">
        {language === "ar"
          ? "المواعيد بتوقيت جهازك:"
          : "Times use your device timezone:"}{" "}
        <bdi>{Intl.DateTimeFormat().resolvedOptions().timeZone}</bdi>
      </p>
      <Card className="calendar-toolbar">
        <div
          className="segmented-control"
          role="group"
          aria-label={language === "ar" ? "عرض التقويم" : "Calendar view"}
        >
          {(["month", "week", "agenda"] as CalendarView[]).map((option) => (
            <button
              key={option}
              type="button"
              className={view === option ? "active" : ""}
              aria-pressed={view === option}
              onClick={() => setView(option)}
            >
              {language === "ar"
                ? { month: "شهر", week: "أسبوع", agenda: "أجندة" }[option]
                : { month: "Month", week: "Week", agenda: "Agenda" }[option]}
            </button>
          ))}
        </div>
        <div className="calendar-navigation">
          <Button
            className="icon-button"
            variant="ghost"
            onClick={() => move(-1)}
            aria-label={
              language === "ar" ? "الفترة السابقة" : "Previous period"
            }
          >
            <IconCaretLeft className="directional-icon" size={18} />
          </Button>
          <Button variant="secondary" onClick={() => setCursor(new Date())}>
            {language === "ar" ? "اليوم" : "Today"}
          </Button>
          <Button
            className="icon-button"
            variant="ghost"
            onClick={() => move(1)}
            aria-label={language === "ar" ? "الفترة التالية" : "Next period"}
          >
            <IconCaretRight className="directional-icon" size={18} />
          </Button>
        </div>
        <strong>
          {view !== "month"
            ? `${weekCells[0]!.toLocaleDateString(language === "ar" ? "ar-EG" : "en-US")} – ${weekCells[6]!.toLocaleDateString(language === "ar" ? "ar-EG" : "en-US")}`
            : cursor.toLocaleDateString(language === "ar" ? "ar-EG" : "en-US", {
                month: "long",
                year: "numeric",
              })}
        </strong>
        <select
          value={platform}
          onChange={(event) => update("platform", event.target.value)}
          aria-label={
            language === "ar" ? "تصفية حسب المنصة" : "Filter by platform"
          }
        >
          <option value="all">
            {language === "ar" ? "كل المنصات" : "All platforms"}
          </option>
          {platforms.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </Card>

      {loading ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ تحميل التقويم…" : "Loading calendar…"
          }
        />
      ) : null}
      {!loading && view === "month" ? (
        <Card className="month-calendar">
          {Array.from({ length: 7 }, (_, index) => {
            const date = new Date(2026, 7, 2 + index, 12);
            return (
              <span className="calendar-weekday" key={index}>
                {date.toLocaleDateString(
                  language === "ar" ? "ar-EG" : "en-US",
                  { weekday: "short" },
                )}
              </span>
            );
          })}
          {monthCells.map((date) => {
            const key = keyFor(date);
            const dayItems = days.get(key) ?? [];
            const outside = date.getMonth() !== cursor.getMonth();
            const today = key === keyFor(new Date());
            return (
              <section
                className={`month-cell ${outside ? "is-outside" : ""} ${today ? "is-today" : ""}`}
                key={key}
              >
                <time dateTime={key}>{date.getDate()}</time>
                <div>
                  {dayItems.slice(0, 3).map((item) => (
                    <Link
                      to={`/app/studio?content=${item.id}`}
                      className={`campaign-chip ${item.platform}`}
                      key={item.id}
                      title={item.title}
                    >
                      <span />
                      {item.title}
                    </Link>
                  ))}
                </div>
                {dayItems.length > 3 ? (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setParams((current) => {
                        const next = new URLSearchParams(current);
                        next.set("view", "agenda");
                        next.set("date", key);
                        return next;
                      });
                    }}
                  >
                    +{dayItems.length - 3}{" "}
                    {language === "ar" ? "عرض الكل" : "View all"}
                  </Button>
                ) : null}
              </section>
            );
          })}
        </Card>
      ) : null}
      {!loading && view === "week" ? (
        <div className="week-calendar">
          {weekCells.map((date) => {
            const key = keyFor(date);
            return (
              <Card className="week-day" key={key}>
                <header>
                  <small>
                    {date.toLocaleDateString(
                      language === "ar" ? "ar-EG" : "en-US",
                      { weekday: "short" },
                    )}
                  </small>
                  <b>{date.getDate()}</b>
                </header>
                {(days.get(key) ?? []).map((item) => (
                  <CalendarItem key={item.id} item={item} language={language} />
                ))}
              </Card>
            );
          })}
        </div>
      ) : null}
      {!loading && view === "agenda" ? (
        <div className="calendar-board">
          {agendaDays.map(([day, scheduled]) => (
            <Card key={day} className="calendar-day">
              <div className="calendar-date">
                <IconCalendar />
                <span>
                  {new Date(`${day}T12:00:00`).toLocaleDateString(
                    language === "ar" ? "ar-EG" : "en-US",
                    { weekday: "long", day: "numeric", month: "long" },
                  )}
                </span>
              </div>
              {scheduled.map((item) => (
                <CalendarItem key={item.id} item={item} language={language} />
              ))}
            </Card>
          ))}
        </div>
      ) : null}
      {!loading &&
      !error &&
      (view === "agenda"
        ? agendaDays.length === 0
        : (view === "week" ? weekCells : monthCells).every(
            (date) => !days.get(keyFor(date))?.length,
          )) ? (
        <EmptyState
          title={
            language === "ar"
              ? "لا توجد مواعيد في هذه الفترة"
              : "No content scheduled in this period"
          }
          body={
            language === "ar"
              ? "أنشئ حملة وحدد موعدًا لتظهر هنا."
              : "Create a campaign and choose a time to see it here."
          }
          action={
            <Link
              className="button button--primary"
              to="/app/studio?tab=campaign"
            >
              {language === "ar" ? "إنشاء حملة" : "Create campaign"}
            </Link>
          }
        />
      ) : null}
    </MotionPage>
  );
}
