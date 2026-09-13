import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  IconChart,
  IconChat,
  IconSpark,
  IconTrend,
} from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
  Pipeline,
} from "../../components/operations";
import { Alert, Card, Spinner, StatCard } from "../../components/ui";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { formatMoney, formatNumber } from "../../lib/format";
import type { AnalyticsSnapshot } from "../../lib/types";

export function AnalyticsPage() {
  const { language } = useLanguage();
  const [data, setData] = useState<AnalyticsSnapshot | null>(null);
  const [channel, setChannel] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .analytics(channel)
      .then(setData)
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setLoading(false));
  }, [channel]);

  const maxRevenue = Math.max(
    ...(data?.top_products.map((item) => Number(item.revenue)) ?? [1]),
    1,
  );

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "التحليلات" : "Analytics"}
        description={
          language === "ar"
            ? "آخر 30 يومًا افتراضيًا · محادثات ومبيعات ومحتوى وأتمتة من بيانات التشغيل الفعلية."
            : "Last 30 days by default · conversations, sales, content, and automation from real operational data."
        }
        action={
          <label className="inline-filter">
            <span>{language === "ar" ? "القناة" : "Channel"}</span>
            <select
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
            >
              <option value="">
                {language === "ar" ? "كل القنوات" : "All channels"}
              </option>
              <option value="webchat">Website</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="instagram_dm">Instagram</option>
              <option value="messenger">Messenger</option>
            </select>
          </label>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {loading ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ حساب المؤشرات…" : "Calculating metrics…"
          }
        />
      ) : (
        data && (
          <>
            <div className="stats-grid">
              <StatCard
                icon={<IconChat />}
                label={language === "ar" ? "المحادثات" : "Conversations"}
                value={formatNumber(data.conversation_volume, language)}
                foot={
                  language === "ar"
                    ? `أول رد ${data.first_response_minutes ?? "—"} دقيقة`
                    : `First response ${data.first_response_minutes ?? "—"} min`
                }
              />
              <StatCard
                icon={<IconTrend />}
                label={
                  language === "ar" ? "الإيراد المنسوب" : "Attributed revenue"
                }
                value={formatMoney(data.attributed_revenue, language)}
                foot={
                  language === "ar"
                    ? `مستعاد ${formatMoney(data.recovered_revenue, language)}`
                    : `Recovered ${formatMoney(data.recovered_revenue, language)}`
                }
              />
              <StatCard
                icon={<IconChart />}
                label={language === "ar" ? "معدل التحويل" : "Conversion rate"}
                value={`${data.conversion_rate}%`}
                foot={`${data.leads} ${language === "ar" ? "عملاء محتملون" : "leads"}`}
              />
              <StatCard
                icon={<IconSpark />}
                label={
                  language === "ar" ? "كفاءة الأتمتة" : "Automation success"
                }
                value={`${data.automation_success_rate}%`}
                foot={`${data.automation_runs} ${language === "ar" ? "تشغيل" : "runs"}`}
              />
            </div>
            <div className="analytics-grid">
              <Card>
                <h2>
                  {language === "ar" ? "قمع التحويل" : "Conversion funnel"}
                </h2>
                <Pipeline
                  items={Object.entries(data.funnel).map(([label, value]) => ({
                    label,
                    value,
                  }))}
                />
              </Card>
              <Card>
                <h2>
                  {language === "ar"
                    ? "إيراد أفضل المنتجات"
                    : "Top product revenue"}
                </h2>
                <div className="bar-chart">
                  {data.top_products.slice(0, 6).map((item, index) => (
                    <div className="bar-row" key={item.product_id}>
                      <span>{item.name}</span>
                      <div>
                        <motion.i
                          initial={{ scaleX: 0 }}
                          animate={{
                            scaleX: Number(item.revenue) / maxRevenue,
                          }}
                          transition={{ delay: index * 0.06 }}
                        />
                      </div>
                      <b>{formatMoney(item.revenue, language)}</b>
                    </div>
                  ))}
                </div>
              </Card>
              <Card>
                <h2>
                  {language === "ar"
                    ? "الطلبات حسب القناة"
                    : "Orders by channel"}
                </h2>
                <div className="donut-wrap">
                  <div
                    className="donut"
                    style={
                      {
                        "--a": `${(Object.values(data.orders_by_channel)[0] ?? 0) * 20}deg`,
                        "--b": `${(Object.values(data.orders_by_channel)[1] ?? 0) * 24}deg`,
                      } as React.CSSProperties
                    }
                  >
                    <span>
                      {Object.values(data.orders_by_channel).reduce(
                        (sum, value) => sum + value,
                        0,
                      )}
                    </span>
                  </div>
                  <div className="legend">
                    {Object.entries(data.orders_by_channel).map(
                      ([name, value]) => (
                        <div key={name}>
                          <span className={`legend-dot ${name}`} />
                          {name}
                          <b>{value}</b>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              </Card>
              <Card>
                <h2>
                  {language === "ar"
                    ? "الذكاء الاصطناعي مقابل الإيراد"
                    : "AI vs revenue"}
                </h2>
                <dl className="metric-list">
                  <div>
                    <dt>
                      {language === "ar"
                        ? "عمليات الذكاء الاصطناعي"
                        : "AI operations"}
                    </dt>
                    <dd>{data.ai_operations}</dd>
                  </div>
                  <div>
                    <dt>
                      {language === "ar"
                        ? "تكلفة الذكاء الاصطناعي المسجلة"
                        : "Recorded AI cost"}
                    </dt>
                    <dd>
                      {data.ai_cost === null
                        ? language === "ar"
                          ? "غير متاحة من المزود"
                          : "Unavailable from provider"
                        : formatMoney(data.ai_cost, language)}
                    </dd>
                  </div>
                  <div>
                    <dt>
                      {language === "ar" ? "منشورات منشورة" : "Published posts"}
                    </dt>
                    <dd>{data.content_published}</dd>
                  </div>
                  <div>
                    <dt>
                      {language === "ar"
                        ? "تفاعلات المحتوى"
                        : "Content engagements"}
                    </dt>
                    <dd>{data.content_engagements}</dd>
                  </div>
                </dl>
              </Card>
            </div>
          </>
        )
      )}
    </MotionPage>
  );
}
