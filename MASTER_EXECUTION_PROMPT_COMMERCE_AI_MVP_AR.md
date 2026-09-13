# البرومبت التنفيذية النهائية — بناء Commerce AI كـ MVP كامل قابل للتشغيل والعرض

أنت الآن فريق تنفيذ مستقل متكامل، ولست مستشارًا يكتب خطة فقط. تصرّف في الوقت نفسه بصفات:

- Senior Product Engineer.
- Software Architect.
- AI/LLM Engineer.
- Backend Engineer.
- Frontend/UX Engineer.
- QA and Security Engineer.
- DevOps Engineer.
- Product Manager وBusiness Analyst.

## المهمة النهائية

حوّل المشروع المرفوع **Deep AI Agent Social** من Scaffold غير مكتمل إلى **MVP حقيقي متكامل يعمل من البداية إلى النهاية** لمنصة تساعد المتاجر الصغيرة على:

1. إضافة صورة وبيانات منتج مرة واحدة، وفهم المنتج بالذكاء الاصطناعي، وإنشاء سجل منظم له.
2. إنشاء محتوى مختلف ومؤسَّس على حقائق المنتج لكل من Facebook وInstagram.
3. عرض المحتوى على التاجر للمراجعة والتعديل، ثم طلب موافقة صريحة محفوظة في الباك إند.
4. النشر الحقيقي على Facebook Page وInstagram Professional Account عند توافر Credentials صحيحة، ثم التحقق من النشر وتسجيل المعرّفات والروابط.
5. استقبال سؤال عميل، وفهم احتياجه، والبحث في المنتجات وسياسات المتجر، وترشيح أفضل ثلاثة منتجات متاحة مع أسباب واضحة، ثم إنشاء رد مبيعات موثّق لا يخترع سعرًا أو مخزونًا أو خاصية أو سياسة.

نفّذ المشروع داخل المستودع نفسه. لا تكتفِ بإخراج تقرير أو عينات كود. عدّل الملفات، أنشئ الملفات اللازمة، احذف البنية الميتة، شغّل الاختبارات، أصلح الأخطاء، وشغّل نسخة الإنتاج محليًا قدر الإمكان.

---

# 1. ترتيب مصادر الحقيقة

اقرأ الملفات المرفوعة أولًا، واستخدمها بهذا الترتيب عند التعارض:

1. **Pasted text.txt**: مصدر الحقيقة لنطاق الـMVP والرحلتين المطلوبتين وما يجب تأجيله.
2. **Pasted text (2).txt**: منهج التحليل والتصميم والتنفيذ والمخرجات، لكن طبّقه بما يخدم نطاق الـMVP فقط ولا تحوّله إلى توسّع غير مطلوب.
3. **Deep_AI_Agent_Social_with_Automated_API_Tests.zip**: النسخة الحالية التي يجب تحليلها وإعادة استخدامها حيث تكون نافعة، وليست معمارية مفروضة.
4. كتب Generative AI Design Patterns وHands-On Software Engineering with Python وSoftware Architecture Patterns: استخدم الفصول والمبادئ ذات الصلة لاتخاذ قرارات عملية، ولا تنتج تلخيصًا عامًا للكتب.
5. في تفاصيل Meta API المتغيرة، تكون **وثائق Meta الرسمية الحالية** هي مصدر الحقيقة. تحقّق منها قبل تثبيت إصدار Graph API أو الصلاحيات أو شكل الاستجابات.

عند تعارض README مع الكود أو الاختبارات، تعامل مع الكود المنفذ والاختبارات الفعلية بوصفهما الحقيقة. لا تعتبر وجود اسم Function أو وصف في README دليلًا على اكتمال الميزة.

---

# 2. تشخيص الحالة الحالية الذي يجب أن تبدأ منه

ابدأ عملك وأنت مدرك لما يلي، ثم تحقّق منه بنفسك وسجّله في `docs/01-current-state.md`:

- المستودع الحالي يعلن بوضوح أنه Scaffold وليس تطبيقًا مكتملًا.
- توجد ثمانية Agent folders وSupervisor وLangGraph وخصائص Orders وAnalytics وInventory وWhatsApp وGoogle Drive وMemory؛ هذا أوسع من نطاق الـMVP الحقيقي.
- يوجد نحو 65 موضعًا يرفع `NotImplementedError` في مسارات الإنتاج.
- الاختبارات الحالية تركز أساسًا على عقود FastAPI وبنية المجلدات، وتحقن `FakeWorkflow`؛ لذلك نجاحها لا يثبت أن Vision أوRAG أوMeta Publishing أوWorkflow يعمل فعليًا.
- بيانات المنتجات التجريبية الحالية أقل من العدد المطلوب.
- لا توجد رحلة واجهة متكاملة للمنتج من رفع الصورة حتى النشر، ولا رحلة مبيعات متكاملة موثقة.

لا تحاول إكمال كل ما في Scaffold. المطلوب هو **إزالة الانحراف عن النطاق** وبناء أصغر منتج متكامل يثبت القيمة.

---

# 3. حدود الـMVP الملزمة

## مطلوب الآن — P0

### المسار A: إضافة المنتج وإنشاء المحتوى ونشره

```text
صورة + اسم + فئة + سعر + مخزون + مواصفات
→ تحقق من المدخلات والملف
→ Vision analysis structured
→ ProductRecord منظم
→ مراجعة وتعديل التاجر للحقائق
→ حفظ المنتج وفهرسته
→ إنشاء Facebook post وInstagram caption مختلفين
→ تحقق برمجي من السعر والخصائص والادعاءات
→ Preview قابل للتعديل
→ موافقة صريحة محفوظة Server-side
→ رفع الصورة إلى Public Image Storage
→ نشر حقيقي على Facebook وInstagram
→ Poll/verify publication
→ حفظ post_id/media_id/permalink/error
```

### المسار B: مساعد المبيعات

```text
سؤال العميل
→ تحديد Intent واستخراج الاحتياج بصيغة منظمة
→ استرجاع منتجات وسياسات ذات صلة
→ تحديث السعر والمخزون من قاعدة الحقيقة
→ فلاتر برمجية للميزانية والفئة والمخزون
→ ترتيب قابل للتفسير
→ أفضل 3 منتجات كحد أقصى
→ رد مؤسَّس على السياق مع References
→ Validator يمنع الحقائق غير المدعومة
```

### واجهة مستخدم كاملة للرحلتين

- Landing page موجزة.
- Login بسيط لحساب Merchant تجريبي واحد.
- Products list بسيطة.
- Product onboarding/publishing wizard.
- Sales assistant.
- Integrations/settings status لعرض حالة LLM وCloudinary وMeta دون كشف أسرار.
- واجهة عربية RTL افتراضيًا، مع دعم واجهة إنجليزية بسيط عبر ملفات ترجمة.
- Responsive على الهاتف وسطح المكتب.

### جودة وتشغيل

- قاعدة بيانات ومخططات وترحيلات.
- Seed لعدد 24 منتجًا على الأقل وسياسات متجر واقعية.
- Unit, integration, API, and minimal E2E tests.
- Dockerized local run.
- توثيق تشغيل ونشر وDemo وأمان وقرارات معمارية.

## غير مناسب للـMVP — احذفه من مسار الإنتاج أو انقله إلى `docs/deferred-scope.md`

- Multi-level أوLLM Supervisor.
- LangGraph orchestration غير الضروري.
- Inventory Agent مستقل؛ المخزون Rule/Repository داخل Product/Sales service.
- Recommendation Agent وSales Support Agent منفصلان؛ ادمجهما في Sales Assistant use case واحد.
- Order tracking.
- Analytics Agent أوتحليل حملات متقدم.
- Customer long-term memory.
- WhatsApp.
- Google Drive import.
- الرد التلقائي على التعليقات.
- Stories/Reels/Carousels.
- Advanced scheduling.
- Multi-store أوMulti-tenant billing.
- الاشتراكات والدفع.
- النشر دون موافقة بشرية.

لا تترك هذه الخصائص ككود ميت يوحي بأنها تعمل. احذفها من Runtime وDependencies وNavigation وTests، ودوّنها فقط في Roadmap.

---

# 4. القرار المعماري الإلزامي

استخدم **Modular Monolith** بسيطًا. لا تستخدم Microservices، ولا Event Bus، ولا Supervisor LLM، ولا Dynamic Agent Creation.

## الطبقات

```text
React Web UI
    ↓ HTTP/JSON
FastAPI API Routes
    ↓
Application Use Cases
    ↓
Domain Models and Deterministic Rules
    ↓
Repositories + AI Provider + Vector Store + Image Storage + Meta Adapters
    ↓
SQLite/PostgreSQL + Chroma + Cloudinary + Meta Graph API
```

### قواعد الفصل

- Routes رفيعة: parsing، authorization، استدعاء use case، mapping response فقط.
- منطق السعر والمخزون والميزانية والقبول والنشر لا يوجد في الواجهة أوPrompt.
- Domain لا يستورد FastAPI أوSQLAlchemy أوLangChain.
- Integrations خلف Protocols/Interfaces قابلة للاستبدال في الاختبارات.
- LLM لا ينسق Workflow ولا يقرر Business rules.
- قاعدة البيانات هي مصدر الحقيقة للسعر والمخزون والمنتج وحالة الموافقة والنشر.
- Vector store للاسترجاع فقط، وليس مصدر حقيقة للقيم المتغيرة.

أنشئ ADRs على الأقل:

- `ADR-001-modular-monolith.md`.
- `ADR-002-remove-llm-supervisor.md`.
- `ADR-003-database-is-source-of-truth.md`.
- `ADR-004-public-image-storage-for-meta.md`.
- `ADR-005-human-approval-before-publishing.md`.

---

# 5. Stack التنفيذ المستهدف

استخدم أقل عدد من المكتبات التي تحقق النتيجة، وثبّت الإصدارات في Lockfiles.

## Backend

- Python 3.11 أوأحدث إصدار متوافق مع كل المكتبات، ولا تستخدم Python pre-release.
- FastAPI.
- Pydantic v2.
- SQLAlchemy 2.x.
- Alembic migrations.
- SQLite في local/demo عبر `DATABASE_URL`، مع إبقاء SQLAlchemy-compatible PostgreSQL path موثقًا للإنتاج.
- Chroma كـVector store محلي persistent للـMVP.
- `langchain-openai` أوOpenAI-compatible SDK واحد فقط، مع Structured Outputs.
- `httpx` للـMeta API.
- Cloudinary كـPublic image storage adapter، مع Local storage adapter للمعاينة المحلية فقط.
- PyYAML لنسخ Prompts versioned.
- pytest، pytest-cov، ruff، mypy أوpyright.

## Frontend

- React + TypeScript + Vite.
- React Router.
- استخدم `fetch` wrapper صغيرًا؛ لا تضف state management library عامة.
- يمكن استخدام React Hook Form + Zod للنماذج فقط.
- CSS variables وCSS modules أوملفات CSS منظمة لبناء Design System محلي. لا تعتمد على CDN في الإنتاج.
- ابنِ Frontend production bundle ثم قدّمه من FastAPI في Docker production حتى يكون النشر Artifact واحدًا.

## ما يجب إزالته إن لم يعد مستخدمًا

- LangGraph.
- Streamlit.
- WhatsApp/Drive/Analytics/Order dependencies.
- أي package لا يوجد له استخدام فعلي.

قبل إضافة Dependency، وثّق سببها في `docs/dependencies.md`.

---

# 6. بنية الملفات المستهدفة

يمكنك تعديل التفاصيل، لكن حافظ على هذه الحدود الواضحة ولا تنشئ مشروعًا جديدًا بجوار القديم:

```text
.
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── error_handlers.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── products.py
│   │       ├── content.py
│   │       ├── publishing.py
│   │       ├── sales.py
│   │       └── health.py
│   ├── application/
│   │   ├── onboard_product.py
│   │   ├── generate_marketing_pack.py
│   │   ├── approve_and_publish.py
│   │   └── assist_customer.py
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   ├── errors.py
│   │   ├── ranking.py
│   │   └── validators.py
│   ├── repositories/
│   │   ├── product_repository.py
│   │   ├── content_repository.py
│   │   ├── publication_repository.py
│   │   └── policy_repository.py
│   ├── services/
│   │   ├── product_intelligence.py
│   │   ├── marketing.py
│   │   ├── sales_assistant.py
│   │   └── search_index.py
│   ├── integrations/
│   │   ├── ai_provider.py
│   │   ├── chroma_store.py
│   │   ├── image_storage.py
│   │   ├── facebook.py
│   │   └── instagram.py
│   ├── prompts/
│   │   ├── product_vision.yaml
│   │   ├── marketing.yaml
│   │   ├── customer_need.yaml
│   │   └── grounded_reply.yaml
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── seed.py
│   ├── static/
│   └── config.py
├── web/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/products/
│   │   ├── features/publishing/
│   │   ├── features/sales/
│   │   ├── lib/api.ts
│   │   ├── i18n/
│   │   └── styles/
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── e2e/
├── alembic/
├── data/seeds/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── Makefile
└── README.md
```

انقل فقط الكود المفيد من البنية القديمة. بعد اكتمال النقل، احذف الملفات القديمة غير المستخدمة ولا تترك بنية مزدوجة.

---

# 7. العقود الأساسية الملزمة

استخدم Pydantic models صارمة `extra="forbid"` لكل البيانات العابرة للحدود. لا تمرر Dictionaries مجهولة بين الوحدات عندما يوجد Contract.

## Product input

```python
class ProductCreateInput(BaseModel):
    product_id: str
    name: str
    category: str
    price: Decimal
    stock: int
    raw_features: list[str]
```

الصورة تُرفع Multipart ولا تُقبل Path عشوائية من العميل.

## Image analysis

```python
class ImageAnalysis(BaseModel):
    product_type: str | None
    colors: list[str]
    materials: list[str]
    visible_features: list[str]
    image_summary: str
    confidence_notes: list[str]
```

## Product record

```python
class ProductRecord(BaseModel):
    product_id: str
    store_id: str
    name: str
    category: str
    price: Decimal
    stock: int
    features: list[str]
    customer_benefits: list[str]
    description: str
    image_summary: str
    original_image_url: str
    public_image_url: str | None
    status: Literal["draft", "reviewed", "active"]
    created_at: datetime
    updated_at: datetime
```

## Marketing pack

```python
class MarketingPack(BaseModel):
    product_id: str
    facebook_message: str
    instagram_caption: str
    hashtags: list[str]
    image_url: str
    validation_warnings: list[str]
    status: Literal["draft", "approved", "published", "partial", "failed"]
```

## Publish result

```python
class PublishResult(BaseModel):
    platform: Literal["facebook", "instagram"]
    success: bool
    external_id: str | None
    permalink: str | None
    error_code: str | None
    error_message: str | None
    raw_status: str | None
```

## Customer need and response

```python
class CustomerNeed(BaseModel):
    intent: Literal[
        "product_search",
        "product_question",
        "product_comparison",
        "policy_question",
        "unsupported"
    ]
    categories: list[str]
    max_budget: Decimal | None
    required_features: list[str]
    use_cases: list[str]
    excluded_features: list[str]
    language: Literal["ar", "en"]
```

```python
class Recommendation(BaseModel):
    product_id: str
    score: float
    reasons: list[str]
```

```python
class SalesAssistantResponse(BaseModel):
    need: CustomerNeed
    recommendations: list[Recommendation]
    reply: str
    citations: list[str]
    insufficient_context: bool
```

استخدم `Decimal` للأموال. حوّلها إلى JSON بصورة آمنة وثابتة. لا تستخدم Float في المقارنات المالية الداخلية.

---

# 8. تنفيذ Product Intelligence

نفّذ Use Case رئيسيًا:

```python
onboard_product(input: ProductCreateInput, image: UploadFile) -> ProductRecord
```

ويتضمن داخليًا:

1. `validate_product_input()`:
   - الاسم والفئة غير فارغين.
   - السعر أكبر من صفر.
   - المخزون صفر أوأكبر.
   - Product ID unique داخل المتجر.
   - MIME مسموح: JPEG/PNG/WebP.
   - تحقق من Magic bytes، لا تعتمد على extension فقط.
   - حد الحجم الافتراضي 10MB من Settings.
   - اسم تخزين UUID، لا تستخدم اسم المستخدم مباشرة.

2. `store_original_image()`:
   - Local adapter في التطوير.
   - Cloudinary adapter عند توافر الإعدادات.
   - لا ترسل Local filesystem path إلى Meta.

3. `analyze_product_image()`:
   - Vision Model حقيقي عبر AIProvider.
   - Structured output مطابق لـ`ImageAnalysis`.
   - Temperature منخفضة.
   - استخرج المرئي فقط.
   - لا تستنتج Bluetooth أوضمان أوقدرة داخلية من الصورة وحدها.
   - عند عدم اليقين، سجّله في `confidence_notes` بدل اختلاق معلومة.

4. `merge_features()`:
   - ادمج raw features والخصائص المرئية.
   - Normalize case/whitespace.
   - إزالة التكرار دون فقد معلومات.
   - لا تجعل الصورة تتغلب على بيانات التاجر الصريحة دون Warning.

5. `generate_informational_description()`:
   - وصف معلوماتي لا إعلان مبالغ فيه.
   - مؤسس على الحقول فقط.

6. `build_product_record()` ثم حفظه Transactionally.

7. `index_product()`:
   - Index النص الدلالي: name، category، features، benefits، description، use cases.
   - لا تعتمد على السعر والمخزون المخزنين في Vector metadata عند الإجابة؛ يجب تحديثهما من DB.
   - Upsert idempotent حسب `store_id + product_id`.

8. واجهة مراجعة تسمح للتاجر بتعديل Features/Benefits/Description قبل تحويل المنتج إلى `active`.

لا تعتبر المنتج جاهزًا للتسويق قبل حالة `reviewed` أو`active`.

---

# 9. تنفيذ Marketing and Approval

نفّذ:

```python
generate_marketing_pack(product_id: str) -> MarketingPack
approve_and_publish(marketing_pack_id: str, platforms: list[str]) -> list[PublishResult]
```

## التوليد

- استخرج Structured marketing brief: hook، benefits، CTA، hashtags.
- Facebook message وInstagram caption يجب أن يكونا مختلفين في الأسلوب والبنية، لا نسختين متطابقتين.
- احترم لغة المنتج/المستخدم.
- السعر والميزات تُمرر إلىPrompt كحقائق صريحة.
- لا تنشئ Discount أوScarcity أوGuarantee غير موجودة.
- لا تستخدم ادعاءات مطلقة مثل “الأفضل” أو“مضمون 100%” دون مصدر.
- اجعل المحتوى قابلًا للتعديل في UI قبل الموافقة.

## Validator حتمي

نفّذ `validate_marketing_content()` في Python قبل الحفظ والنشر:

- كل رقم سعر مذكور يطابق السعر الحالي.
- الخصائص المذكورة subset من ProductRecord facts.
- لا يوجد خصم ما لم يوجد حقل خصم صريح، وهو غير موجود في MVP؛ إذن أي Discount claim مرفوض.
- لا يوجد ادعاء Stock/limited quantity إلا إذا تم توليده Deterministically من المخزون وبقواعد معلنة؛ الأفضل عدم استخدامه في MVP.
- الصورة public URL عند طلب Meta publish.
- لا تُنشر Draft فيه Warnings حرجة.

## الموافقة

- Approval ليست Boolean يرسله Frontend وحده.
- احفظ `approved_at`، `approved_by`، وHash/Version للمحتوى الموافق عليه.
- أي تعديل بعد الموافقة يلغيها ويعيد الحالة إلى Draft.
- Endpoint النشر يرفض HTTP 409 أوDomain error إذا لم توجد موافقة سارية.
- لا يوجد Auto-publish.

---

# 10. تنفيذ Meta Publishing الحقيقي

استخدم Adapter مستقل لكل منصة، وحقن Dependency في Use Case.

## Settings المطلوبة

```text
ENABLE_REAL_PUBLISHING=false
META_GRAPH_API_BASE=https://graph.facebook.com
META_GRAPH_API_VERSION=<verified-current-version>
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
INSTAGRAM_USER_ID=
INSTAGRAM_ACCESS_TOKEN=
META_POLL_INTERVAL_SECONDS=2
META_POLL_TIMEOUT_SECONDS=60
```

لا تطبع Tokens ولا تعيدها في API أوLogs.

## Facebook

- نشر صورة على Facebook Page باستخدام endpoint الرسمي الحالي المناسب، بالـPage Access Token.
- مرّر Public HTTPS image URL وmessage.
- افحص HTTP status وMeta error payload.
- خزّن external post ID.
- حاول جلب permalink عبر endpoint رسمي إذا كانت الصلاحيات تسمح.
- ميّز بين configuration error، permission error، rate limit، invalid image، وtransient network error.

## Instagram

Workflow ملزم:

1. Create media container.
2. Poll `status_code` بحد أقصى وExponential أوFixed bounded backoff.
3. حالات النجاح والفشل تُفسر بوضوح.
4. عند `FINISHED` فقط، نفّذ `media_publish`.
5. خزّن media ID.
6. جلب permalink إن أمكن.

لا تستخدم فحصًا واحدًا ثم تفشل فورًا؛ Container قد يحتاج وقتًا. لا تستخدم Retry غير محدود.

## Feature flag والسلوك دون Credentials

- الاختبارات العادية تستخدم Fake publishers ولا تتصل بـMeta.
- إذا كان `ENABLE_REAL_PUBLISHING=false`، ارجع حالة واضحة `publishing_disabled` ولا تزعم نجاحًا.
- إذا كان Flag true وCredentials ناقصة، افشل Configuration validation عند startup أوعند اختبار الاتصال برسالة مفهومة.
- أضف `scripts/meta_smoke_test.py` لا يعمل إلا عند `RUN_META_SMOKE_TESTS=true` وموافقة صريحة.
- لا تنشر أي محتوى من الاختبارات تلقائيًا.

## صفحة Integrations

اعرض فقط:

- Configured / Not configured.
- آخر Connection check.
- Facebook Page ID masked.
- Instagram User ID masked.
- لا تعرض Tokens.

---

# 11. تنفيذ Sales RAG and Recommendation

نفّذ Use Case واحدًا:

```python
assist_customer(store_id: str, message: str) -> SalesAssistantResponse
```

## 11.1 Intent وNeed extraction

- استخدم Structured Output لـ`CustomerNeed`.
- أسماء الفئات المسموحة تأتي من Repository، لا من قائمة ثابتة داخل Prompt.
- الميزانية تُستخرج كرقم، لكن المقارنة تتم في Python.
- لا تطلب Clarification إلا إذا كانت المعلومة ستغير القرار فعلًا.
- في MVP، عندما توجد معلومات كافية جزئيًا، أعط أفضل النتائج المتاحة واذكر القيد بدل تعطيل المستخدم بأسئلة كثيرة.

## 11.2 Retrieval

- ابحث في Product index وPolicy index كل على حدة.
- top_k الأولي = 7 منتجات.
- خزّن citations مستقرة مثل `product:P100` و`policy:returns#section-2`.
- طبّق out-of-domain threshold قابلًا للضبط. إذا لم توجد معرفة كافية، لا تخترع جوابًا.

## 11.3 Hard filters في Python

استبعد حتميًا:

- `stock <= 0`.
- `price > max_budget` عندما توجد ميزانية صريحة.
- الفئة غير المتوافقة صراحة.
- excluded features الصريحة.

الـLLM ممنوع من تقرير أن السعر “داخل الميزانية” دون مقارنة برمجية.

## 11.4 Ranking قابل للتفسير

استخدم دالة واضحة موثقة واختبرها. نقطة بدء مقبولة:

```text
score =
    feature_match * 0.50
  + budget_match  * 0.25
  + use_case_match * 0.25
```

- كل component بين 0 و1.
- semantic retrieval score يمكن استخدامه داخل feature/use-case match، ولا تضف وزنًا خفيًا غير موثق.
- Tie-breaker: أعلى توافق، ثم أقل سعر، ثم product_id لضمان determinism.
- أعد أفضل 3 فقط.
- Reason لكل منتج مشتق من Matches فعلية، لا من نص حر غير متحقق.

## 11.5 Grounded reply

- مرّر إلى الموديل فقط المنتجات النهائية والسياسات المسترجعة.
- اطلب صيغة منظمة أولًا، ثم Render الرد النهائي.
- السعر والمخزون والميزات في الرد يجب أن تأتي من DB snapshot الحالي.
- كل Policy claim له citation.
- عند السؤال عن شيء غير موجود، قل بوضوح إن المعلومات غير متاحة.
- لا تستخدم Memory طويلة الأجل في MVP.

## 11.6 Reply validator

تحقق آليًا من:

- كل Product ID في الرد موجود ضمن النتائج.
- كل سعر مذكور يطابق DB.
- كل خاصية مذكورة موجودة في ProductRecord.
- كل citation موجود في retrieved context.
- عدد الترشيحات ≤3.
- لا توجد توصية Out of stock أوفوق الميزانية.

عند فشل Validation، نفّذ إعادة توليد واحدة فقط باستخدام قائمة الأخطاء. إذا فشلت ثانية، استخدم Reply template حتميًا من البيانات بدل إرجاع Hallucination.

---

# 12. أنماط GenAI الواجب تطبيقها عمليًا

استخدم هذه المبادئ في الكود، لا في تقرير نظري فقط:

1. **Grammar/Structured Outputs**: كل تحليل Vision وNeed وMarketing brief وGrounded response له Pydantic schema.
2. **Basic RAG بصورة غير مبالغ فيها**: indexing → retrieval → generation، مع فصل Product وPolicy collections.
3. **Trustworthy Generation**: citations، out-of-domain detection، human approval، validation، ورفض الإجابة عند نقص المعرفة.
4. **Tool Calling / External Actions**: النشر فعل حقيقي خلف Adapter، لا نص يدّعي أنه نشر.
5. **Dependency Injection**: AI،Repositories،Vector store،Storage،Publishers قابلة للاستبدال بفakes.
6. **Reflection محدود**: إعادة محاولة واحدة عند فشل schema أوvalidator، ثم fallback حتمي؛ لا حلقات ذاتية مفتوحة.
7. **Guardrails**: factual allowlists، budget/stock rules، approval gate، file validation، secret handling.
8. **Inference testing**: dataset صغير ثابت لأسئلة عربية/إنجليزية واختبار عدم اختراع حقائق، لا تعتمد فقط على Unit tests تقليدية.

لا تطلب من الموديل إظهار Chain of Thought. احتفظ فقط بأسباب قصيرة قابلة للتدقيق داخل الحقول المطلوبة.

---

# 13. قاعدة البيانات

استخدم الجداول التالية على الأقل:

## stores

- id، slug، name، default_language، created_at.

## products

- id، store_id، product_id، name، category، price_numeric، stock، features_json، benefits_json، description، image_summary، original_image_url، public_image_url، status، created_at، updated_at.
- Unique `(store_id, product_id)`.

## marketing_packs

- id، store_id، product_id FK، facebook_message، instagram_caption، hashtags_json، image_url، validation_warnings_json، version، status، approved_at، approved_by، approved_content_hash، created_at، updated_at.

## publications

- id، marketing_pack_id، platform، status، external_id، permalink، error_code، error_message، request_id، attempted_at، completed_at.
- Idempotency key لمنع النشر المكرر عند إعادة Request.

## policies

- id، store_id، policy_type، title، body، source_ref، updated_at.

## sales_queries

- id، store_id، message، parsed_need_json، recommended_product_ids_json، response_text، citations_json، created_at.
- لا تخزن PII حساسة.

## audit_events

- id، actor، action، entity_type، entity_id، metadata_json منزوعة الأسرار، created_at.

أنشئ Alembic migration أولية وSeed idempotent. لا تستخدم `create_all()` كبديل دائم للترحيلات في production startup.

---

# 14. API الملزمة

استخدم Prefix `/api/v1`، وأضف OpenAPI examples.

## Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

MVP Auth:

- حساب Merchant واحد من Environment أوSeed.
- Password hash آمن، لا plaintext في repo.
- Signed HttpOnly Secure session cookie في production.
- SameSite مناسب وCSRF protection للطلبات المعدلة للحالة.
- لا Public registration ولاPassword reset في MVP.

## Products

- `GET /api/v1/products`
- `POST /api/v1/products/onboard` multipart.
- `GET /api/v1/products/{product_id}`.
- `PATCH /api/v1/products/{product_id}` للمراجعة والتعديل.
- `POST /api/v1/products/{product_id}/activate`.

## Marketing

- `POST /api/v1/products/{product_id}/marketing-packs`.
- `GET /api/v1/marketing-packs/{id}`.
- `PATCH /api/v1/marketing-packs/{id}`؛ أي تعديل يلغي الموافقة.
- `POST /api/v1/marketing-packs/{id}/approve`.

## Publishing

- `POST /api/v1/marketing-packs/{id}/publish` مع platforms وIdempotency key.
- `GET /api/v1/publications/{id}`.
- `POST /api/v1/integrations/meta/check` لا ينشر شيئًا.

## Sales

- `POST /api/v1/sales/assist`.

## System

- `GET /health/live`.
- `GET /health/ready` يفحص DB وVector store فقط، ولا يجري LLM/Meta call مكلفًا في كل Health check.

## Errors

استخدم Envelope ثابتًا:

```json
{
  "error": {
    "code": "content_not_approved",
    "message": "المحتوى يحتاج إلى موافقة قبل النشر.",
    "details": {},
    "request_id": "..."
  }
}
```

- 400 invalid business input.
- 401 unauthenticated.
- 403 forbidden.
- 404 missing entity.
- 409 invalid state/idempotency conflict.
- 422 schema errors.
- 502 external provider error.
- 503 integration not configured/unavailable.

لا تعرّض stack traces أوprovider secrets للعميل.

---

# 15. UX والواجهة

## فلسفة الواجهة

- المستخدم الأساسي: صاحب متجر صغير أوSocial media operator بخبرة تقنية منخفضة إلى متوسطة.
- وعد المنتج الظاهر: **“أضف منتجك مرة واحدة، أنشئ محتواه، انشره، واستخدم بياناته لتحويل أسئلة العملاء إلى فرص بيع.”**
- يجب أن يصل المستخدم إلى أول Preview مفيد خلال أقل من 3 دقائق في بيانات Demo.
- Progressive disclosure: لا تعرض إعدادات Meta أوتفاصيل RAG داخل رحلة المنتج إلا عند الحاجة.
- كل شاشة لها Primary action واحد واضح.

## الصفحات

### `/`

- Hero يشرح المشكلة والنتيجة خلال ثوانٍ.
- CTA إلى Demo login.
- 3 خطوات فقط: Add product، Review content، Publish & sell.
- لا تملأ الصفحة بميزات مؤجلة.

### `/login`

- Email/password.
- رسائل خطأ آمنة.
- بيانات Demo تُذكر فقط في Development mode.

### `/app/products`

- قائمة المنتجات، search بسيط، status، stock، price، زر “إضافة منتج”.
- Empty state يقود إلى onboarding.

### `/app/products/new`

Wizard واضح:

1. إدخال البيانات والصورة.
2. تحليل AI مع Progress state.
3. مراجعة Product facts؛ الحقول القابلة للتعديل واضحة، والحقائق المستخرجة من الصورة مميزة.
4. تفعيل المنتج.
5. توليد محتوى.
6. Preview منفصل Facebook/Instagram.
7. تعديل → Validate → Approve.
8. Publish مع Confirmation dialog.
9. Result cards وروابط المنشورات أوأخطاء قابلة للإصلاح.

حالات مطلوبة:

- upload progress.
- unsupported file.
- LLM unavailable.
- partial image analysis.
- content validation warnings.
- publishing disabled.
- one platform succeeded and the other failed.
- expired/permission-denied token.
- retry button لا يؤدي إلى Duplicate post بفضل idempotency.

### `/app/sales`

- Message composer بأمثلة عربية.
- Structured need summary يمكن طيه.
- Top 3 product cards: الصورة، الاسم، السعر، حالة التوفر، reasons.
- Reply box قابل للنسخ.
- Citations section.
- Empty/no-match/out-of-domain states صريحة.

### `/app/integrations`

- حالة AI، image storage، Facebook، Instagram.
- تعليمات إعداد مختصرة.
- Test connection لا ينشر.
- لا تعرض Secret values.

## Design System

أنشئ `web/src/styles/tokens.css` وComponents reusable:

- Buttons: primary، secondary، destructive، ghost، loading، disabled.
- Inputs، textarea، select، file upload dropzone.
- Cards، badges، tabs، stepper، alerts، toast، modal، skeleton، spinner، empty state.
- Product card، recommendation card، platform preview، publish result.

المتطلبات:

- CSS variables للألوان والمسافات والTypography والRadius والShadow.
- WCAG AA contrast.
- Focus states ظاهرة.
- Keyboard navigation.
- Labels وARIA للأيقونات والDialogs.
- RTL حقيقي، لا مجرد `text-align:right`.
- Mobile first.
- تجنب Animation الزائدة؛ احترم `prefers-reduced-motion`.
- لا تستخدم نصوص Lorem Ipsum أوButtons بلا وظيفة.

---

# 16. Seed data

أنشئ 24–30 منتجًا واقعيًا على الأقل موزعة على فئات مثل:

- Headphones/Audio.
- Phones/Accessories.
- Home appliances الصغيرة.
- Skincare أوFashion accessories إن كانت السياسات عامة.

كل منتج يحتوي على:

- ID ثابت.
- سعر EGP.
- مخزون متنوع، ويشمل منتجات نفدت لاختبار الفلاتر.
- 4–8 features.
- 2–4 use cases/benefits.
- وصف قصير.
- Local generated SVG/JPEG placeholder آمن للـDemo، دون نسخ صور محمية.

أنشئ سياسات عربية وإنجليزية للشحن والاسترجاع والضمان، مع Source IDs مستقرة وفقرات يمكن الاستشهاد بها.

أنشئ 15 سؤال تقييم على الأقل، منها:

- “عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه”.
- سؤال فوق الميزانية.
- سؤال عن منتج Out of stock.
- سؤال مقارنة.
- سؤال سياسة استرجاع.
- سؤال خارج النطاق.
- أسئلة English equivalents.

---

# 17. الاختبارات ومعايير الجودة

لا تكتفِ باختبارات FakeWorkflow القديمة. أعد كتابة Test suite لتثبت السلوك الحقيقي.

## Unit tests

- Product validation and file validation.
- Feature merge.
- Money/budget filters.
- Ranking components and deterministic tie-breaker.
- Marketing factual validator.
- Approval invalidation after edit.
- Reply validator.
- Meta error mapping and bounded polling.

## Integration tests

- DB repositories with temporary SQLite.
- Chroma index upsert/search.
- Product onboarding with FakeAIProvider.
- Marketing generation and approval.
- Publish with FakeFacebook/FakeInstagram.
- Sales assist against seeded products/policies.

## API tests

- كل endpoint happy path وinvalid states.
- Auth/CSRF.
- Multipart file limits.
- Approval gate.
- Idempotency prevents duplicate publishing.
- Safe external error responses.

## E2E tests

باستخدام Playwright أوبديل واحد فقط:

1. Login → onboard product → review → generate content → approve → fake publish → result.
2. Ask sales question → see ≤3 valid products → copy grounded reply.

## AI evaluation tests

- Fake deterministic provider للـCI.
- Optional live evals خلف `RUN_LIVE_AI_EVALS=true`.
- Assertions على schema، grounded product IDs، budget compliance، citation validity.
- لا تجعل CI يتطلب API key.

## Gates النهائية

شغّل وأصلح حتى تنجح:

```bash
ruff check .
ruff format --check .
mypy app
pytest --cov=app --cov-report=term-missing
npm --prefix web run lint
npm --prefix web run test
npm --prefix web run build
```

استهدف Coverage لا يقل عن 80% في Domain/Application core. لا تتلاعب بالاستثناءات للوصول إلى الرقم.

نفّذ أيضًا:

```bash
grep -R "NotImplementedError" app tests
```

والنتيجة المطلوبة صفر في كود الإنتاج. لا تترك `pass` أوTODO في P0 paths.

---

# 18. الأمان والخصوصية

نفّذ وليس فقط وثّق:

- Secrets من Environment فقط.
- `.env` في `.gitignore` و`.env.example` بلا قيم حقيقية.
- Redaction filter للLogs يخفي Tokens/API keys.
- Request ID لكل طلب.
- Structured logging دون محتوى صورة أوPrompt كامل افتراضيًا.
- File content validation، limits، UUID names، ومنع path traversal.
- Input length limits لرسائل العميل والمحتوى.
- Escape user-generated text في UI.
- CORS محدود في Development، same-origin في Production.
- Secure headers الأساسية.
- Auth session وCSRF كما سبق.
- Rate limit بسيط لمسارات AI وPublishing إن كان سهلًا ضمن نفس التطبيق؛ إن تعذر دون Dependency ثقيلة، وثّق Reverse-proxy limit المطلوب قبل public launch.
- لا تخزن محادثات حساسة أوPII غير لازمة.
- Audit event للموافقة والنشر.
- License inventory في `docs/third-party-licenses.md`.

---

# 19. Observability ومعالجة الأخطاء

- استخدم Python logging موحدًا بصيغة JSON أوstructured fields.
- سجّل: request_id، use_case، entity_id، duration_ms، provider، success/failure، error_code.
- لا تسجل token أوbinary image أوكامل customer message في Production؛ استخدم length/hash عند الحاجة.
- Timeouts لكل LLM/Cloudinary/Meta request.
- Retry مرة واحدة فقط للـnetwork transient errors مع backoff، وليس لأخطاء 4xx.
- Circuit breaker ليس مطلوبًا للـMVP.
- Health live/ready كما سبق.
- واجهة تظهر Partial success بصراحة.

---

# 20. التشغيل والنشر

أنشئ:

- `pyproject.toml` وlock/pinned dependencies.
- `web/package-lock.json` أوlockfile مكافئ.
- `Makefile` بالأوامر:

```text
make setup
make migrate
make seed
make dev
make test
make build
make run-prod
```

- Multi-stage `Dockerfile`: build React ثم install Python ثم copy static build.
- `docker-compose.yml` لتشغيل التطبيق محليًا مع volumes للـDB/Chroma/uploads.
- Production config لا يستخدم Vite dev server.
- README من الصفر يشرح Local run في أقل خطوات ممكنة.
- `docs/deployment.md` لخيار Render/Railway/Fly.io أوأي Docker host مع persistent disk وHTTPS.
- Backup instructions لـSQLite/Chroma، وخطة migration إلى PostgreSQL/pgvector بعد الـMVP.
- Rollback: immutable image tag + DB backup قبل migration.

لا تعتمد على Vercel serverless للباك إند الذي يحتاج ملفات persistent وChroma local.

---

# 21. المخرجات الوثائقية المطلوبة داخل المستودع

أنشئ ملفات قصيرة وعملية، لا تقارير إنشائية:

1. `docs/01-current-state.md`: ما كان موجودًا، ما حُذف، ما أُعيد استخدامه.
2. `docs/02-product-strategy.md`: المشكلة، المستخدم الأساسي، القيمة، مؤشرات النجاح.
3. `docs/03-ux-spec.md`: journeys، flows، pages، states، accessibility.
4. `docs/04-design-system.md`: tokens، components، usage rules.
5. `docs/05-architecture.md`: components، boundaries، data flow، failure points.
6. `docs/06-api.md`: endpoints وأمثلة وأخطاء، مع الإشارة إلى OpenAPI.
7. `docs/07-security.md`.
8. `docs/08-test-plan.md`.
9. `docs/09-deployment.md`.
10. `docs/10-demo-script.md`.
11. `docs/11-business.md`: business model، MVP pricing hypothesis، go-to-market أولي، assumptions.
12. `docs/deferred-scope.md`.
13. `docs/risks-and-assumptions.md`.
14. ADR files.
15. `FINAL_REPORT.md`.

## مؤشرات نجاح عملية

استخدم على الأقل:

- Time to first valid product record.
- Time from product upload to content preview.
- Publish success/partial failure rate.
- Percentage of recommendation responses with zero factual violations.
- Percentage of recommendations respecting stock and budget.
- Sales answer citation coverage.
- Task completion rate للمسارين.
- Demo completion time المستهدف أقل من 5 دقائق.

## فرضية التسعير، لا حقيقة غير مختبرة

قدّم نموذجًا أوليًا بسيطًا في docs، مثل:

- Free demo محدود.
- Starter اشتراك شهري بعدد منتجات/منشورات محدود.
- لا تنفذ Billing في MVP.

اكتب بوضوح أن السعر Hypothesis يحتاج مقابلات وتجارب بيع.

---

# 22. سيناريو الـDemo الإلزامي

يجب أن ينجح محليًا دون Credentials حقيقية باستخدام Fakes، ويعمل بالنشر الحقيقي عند ضبطها:

1. تسجيل الدخول بالحساب التجريبي.
2. رفع صورة سماعة وإدخال السعر 1200 والمخزون 8 والميزات Bluetooth/Microphone.
3. ظهور Vision analysis منظم، مع مراجعة وتصحيح المستخدم.
4. حفظ المنتج وفهرسته.
5. توليد Facebook وInstagram content مختلفين.
6. تعديل كلمة واحدة ثم ملاحظة أن Approval غير موجود.
7. Validate ثم Approve.
8. Publish:
   - في Fake mode: نتيجتا نجاح واضحتان وموسومتان Demo، دون الادعاء أنهما منشورات حقيقية.
   - في Real mode: post/media IDs وروابط فعلية من Meta.
9. الانتقال إلى Sales Assistant وكتابة:
   “عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه”.
10. ظهور المنتج ضمن أفضل ثلاثة، بسعره الصحيح، وسبب حقيقي، ورد موثّق.
11. سؤال سياسة استرجاع وظهور citation.
12. سؤال خارج النطاق ورفض مهذب دون Hallucination.

أنشئ Screenshot-ready UI وبيانات ثابتة تجعل هذا السيناريو مستقرًا.

---

# 23. طريقة العمل الإلزامية

نفّذ بالترتيب التالي، لكن **لا تتوقف لطلب موافقة بعد كل مرحلة**:

## المرحلة 1 — Audit

- افتح كل ملفات المشروع الحالية.
- افحص جميع `NotImplementedError` والDependencies والTests.
- افحص مستندات المشروع والمقاطع ذات الصلة من الكتب.
- اكتب `docs/01-current-state.md` وScope matrix.

## المرحلة 2 — Scope reduction

- احذف/انقل كل الخصائص المؤجلة.
- أزل LangGraph وSupervisor والبنية ذات الثمانية Agents.
- ثبّت Contracts الجديدة.
- حدّث README وTests التي كانت تفرض البنية القديمة.

## المرحلة 3 — Backend core

- Config،DB،migrations،repositories،domain rules.
- Product intelligence.
- Search index.
- Marketing،approval،publishing adapters.
- Sales assistant.
- Auth/error handling/logging.

## المرحلة 4 — Frontend

- Design tokens/components.
- الرحلات والصفحات والحالات كاملة.
- Arabic RTL + English strings.
- API integration.

## المرحلة 5 — Quality

- Seed.
- Unit/integration/API/E2E tests.
- Build/lint/typecheck.
- Fix all failures.

## المرحلة 6 — Delivery

- Docker run.
- Smoke tests.
- Docs،Demo script،business/risks.
- `FINAL_REPORT.md`.

اجعل المشروع قابلًا للتشغيل بعد كل مرحلة كبيرة. استخدم Commits منطقية إن كانت بيئة Git متاحة.

---

# 24. قواعد تمنع الفشل الشائع

- لا تنفذ Architecture Astronautics.
- لا تضف Agent لمجرد أن المشروع اسمه AI Agent.
- لا تستخدم LLM فيما يمكن أن يكون شرطًا برمجيًا.
- لا تخلط `price` أو`stock` داخل Prompt ثم تثق في النص الناتج دون Validator.
- لا تجعل Approval في الواجهة فقط.
- لا تدّع النشر عند غياب Meta response ناجحة.
- لا تستخدم image local path مع Instagram.
- لا تخزّن Access Tokens في DB أوFrontend.
- لا تكتب Mock data داخل Production code paths.
- لا تجعل Tests تتصل بخدمات حقيقية افتراضيًا.
- لا تترك dead code من النسخة القديمة.
- لا تجعل README أكبر من المنتج.
- لا تعتبر passing contract tests دليل End-to-End.
- لا تنشئ أسئلة Clarification كثيرة تجعل المساعد معطلًا.
- لا تظهر confidence score وهميًا من LLM على أنه قياس علمي؛ استخدم Notes أوretrieval thresholds قابلة للاختبار.
- لا تخفِ Partial failures.
- لا تغيّر حقائق المنتج في Marketing copy.
- لا تطبع Chain of Thought.

---

# 25. التعامل مع المعلومات الناقصة

لا تسأل المستخدم أسئلة عامة يمكن حسمها بقرار هندسي معقول. دوّن افتراضاتك في `docs/risks-and-assumptions.md`.

يمكنك التوقف وطلب Input فقط عند Blocker خارجي حقيقي، مثل:

- Meta credentials غير متاحة لإجراء Smoke test حقيقي.
- Cloudinary credentials غير متاحة لاختبار Public upload.
- LLM key غير متاح لاختبار Live provider.

حتى عند غياب هذه الأسرار:

- أكمل كل الكود والواجهات والاختبارات باستخدام Fakes.
- شغّل المشروع في Demo mode.
- لا تضع قيمًا زائفة في `.env` وتدّعي أنها حقيقية.
- اكتب قائمة دقيقة بالاختبارات الحية التي لم تُنفذ ولماذا.

---

# 26. تعريف الاكتمال النهائي

لا تقل إن المشروع اكتمل إلا إذا تحققت كل الشروط التالية:

- لا يوجد `NotImplementedError` أوTODO في P0 runtime.
- الرحلتان تعملان End-to-End محليًا.
- Product image → structured record → save → index يعمل.
- Marketing generation → validation → edit → approval → publish adapter يعمل.
- Meta real path منفذ وفق الوثائق، حتى لو تعذر Smoke test لغياب Credentials.
- Sales RAG يعيد ≤3 منتجات حقيقية ويحترم stock/budget.
- Reply validation يمنع السعر/الميزة/السياسة المختلقة.
- واجهة Responsive وRTL وحالات الخطأ/التحميل/الفراغ مكتملة.
- Seed ≥24 products.
- Migrations وDocker وREADME يعملون.
- Lint/typecheck/tests/build ناجحة فعلًا أويوجد Blocker موثق بدقة.
- لا توجد أسرار في المستودع.
- `FINAL_REPORT.md` يذكر بصدق ما نُفذ وما لم يُختبر حيًا.

## صيغة رسالتك النهائية بعد التنفيذ

قدّم فقط:

1. ملخصًا لما بنيته.
2. أهم قرارات التبسيط وما حُذف من Scaffold.
3. أوامر التشغيل.
4. الاختبارات التي شغلتها ونتائجها الفعلية.
5. حالة Real Meta/Cloudinary/LLM smoke tests.
6. القيود المتبقية والملفات المرجعية.

لا تضع خطة مستقبلية طويلة بدل المنتج. لا تدّع نجاح شيء لم تشغله.

**ابدأ الآن من جذر المستودع. نفّذ Audit سريعًا، ثم استمر تلقائيًا في إعادة البناء والتنفيذ والاختبار حتى يصبح الـMVP قابلًا للتشغيل والعرض.**
