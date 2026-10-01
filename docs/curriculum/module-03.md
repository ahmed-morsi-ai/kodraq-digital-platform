# Module 03 — HTTP & Networking / الشبكات وتشخيص طلبات الويب

## Learning outcomes / مخرجات التعلّم

ستفسّر URL والـorigin، تميّز فشل الشبكة عن فشل HTTP، وتختار خطوات تشخيص مبنية على الأدلة. ستفهم العقد الخاص بالطريقة والمسار ونوع المحتوى، وتختبر تسجيل الدخول دون كشف credentials أو تغيير نظام المصادقة عشوائياً.

## 1. من الاسم إلى التطبيق / Layers

طلب الويب يمر عبر طبقات مختلفة. اسم المضيف يحتاج حلاً إلى عنوان مناسب، ثم اتصال نقل، وقد يسبقه تفاوض TLS، ثم معالجة HTTP. HTTP/1.1 وHTTP/2 يستخدمان عادة TCP، بينما HTTP/3 يستخدم QUIC فوق UDP. تغيير المنفذ قد يصل إلى تطبيق مختلف تماماً على الجهاز نفسه. مرجع النسخة الثالثة: [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html).

`http://localhost:5173` و`http://localhost:8000` لهما origin مختلف لأن المنفذ مختلف. في إعداد التطوير الأول عادة خادم Vite، والثاني FastAPI. reverse proxy يستطيع تمرير `/api/v1/...` إلى Backend مع الحفاظ على المسار. أما client base URL فيحدد أين يرسل المتصفح الطلب ابتداءً.

افصل TCP connection refused عن رد HTTP 404. الأول قد يعني أن لا خدمة تستمع أو أن الاتصال مُنع؛ الثاني يعني أن خدمة HTTP ردّت ولم تجد المورد وفق عقدها. افحص الرد وheaders وعنوان الطلب الفعلي، لا الرسالة العامة في واجهة المستخدم فقط.

## 2. العقد: method + path + representation

المسار وحده لا يكفي. `POST /api/v1/login/access-token` يستقبل نموذج تسجيل الدخول، بينما فتح الرابط في شريط المتصفح يرسل GET. إذا وُجد المسار لكن الطريقة غير مدعومة، فالرد المعتاد 405. ليس الحل إضافة GET عشوائياً إلى login.

HTTP methods carry semantics: GET retrieves a representation; POST asks a resource to process submitted content. PUT and DELETE have idempotent semantics, while POST does not generally guarantee that. Repeated DELETE may return a different status without contradicting idempotency of its intended effect. [HTTP semantics, methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-method-definitions).

`Content-Type` يصف representation المرسلة، و`Accept` يعبّر عما يقبله العميل في الرد. في مشروعنا registration يرسل JSON، وtoken login يرسل `application/x-www-form-urlencoded`. إرسال أسماء حقول خاطئة أو representation غير مناسبة قد يصل إلى المسار ثم يفشل التحقق.

```sh
curl -i http://localhost:8000/api/v1/users/me
curl -i -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" -d '{}'
curl -i -X POST http://localhost:8000/api/v1/login/access-token \
  -H "Content-Type: application/x-www-form-urlencoded" --data ''
```

الأوامر السابقة لا تحتاج بيانات اعتماد ولا تنشئ حساباً صالحاً. في هذا التطبيق نتوقع 401 للملف الشخصي غير الموثق و422 للطلبات الناقصة. هذه حالات فشل متوقعة تثبت الوصول إلى route، وليست اختبارات نجاح login.

## 3. قراءة status codes بدون تخمين

| Code | Interpretation / الاستخدام |
| --- | --- |
| 200 / 201 | نجحت العملية / أُنشئ مورد وفق عقد الخدمة |
| 307 | تحويل مؤقت يحافظ على method؛ افحص Location قبل اتباعه |
| 400 | الطلب مرفوض وفق عقد التطبيق؛ كلمة مرور خاطئة تستخدمه هنا |
| 401 / 403 | مصادقة مطلوبة أو غير صالحة / الطلب ممنوع |
| 404 / 405 | المورد غير موجود / الطريقة غير مدعومة |
| 409 / 422 | تعارض حالة / تعذر معالجة المدخلات وفق العقد |
| 429 / 503 | تجاوز معدل / الخدمة غير متاحة مؤقتاً |

Status meanings come from the HTTP contract; application details still matter. Do not replace a observed 400 with an expected 401 just to match a tutorial. Do not assume a 404 proves whether a private resource exists: some systems intentionally conceal that distinction. [RFC 9110 status codes](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes).

## 4. CORS وTLS وأمان المتصفح

CORS سياسة وصول يطبقها المتصفح على طلبات cross-origin، وليست نظام authentication. طلب `curl` قد ينجح بينما يمنع المتصفح قراءة الرد. افحص preflight من نوع OPTIONS والـorigin المسموح والـheaders الفعلية. تجنّب علاج كل خطأ بإتاحة جميع origins مع credentials. [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS).

TLS يحمي الاتصال وفق إعداداته؛ لا يقرر صلاحية الطالب للوصول إلى مسار تعليمي. token صالح لا يساوي تصريحاً لكل track. لا تضع API key الخاصة بالـembedding داخل متغير يبدأ بـ `VITE_` لأنه إعداد يصل إلى واجهة المتصفح. سجّل status وrequest ID بدلاً من Authorization header.

## 5. تشخيص 404 محلياً / Diagnostic sequence

1. انسخ Request URL وmethod من Network tab، واحذف البيانات السرية قبل المشاركة.
2. جرّب endpoint على Backend مباشرة، ثم عبر Vite proxy؛ قارن status وContent-Type.
3. افحص `/api/v1/openapi.json` وتأكد أن خدمة Backend الفعلية تحتوي routes المطلوبة.
4. تحقق أن `VITE_API_URL` هو origin فقط؛ لا تضف `/api/v1` مرتين.
5. افحص trailing slash مع تعطيل اتباع التحويل أولاً؛ لا تغيّر المسار قبل رؤية Location.
6. إذا كانت الصورة المحلية قديمة، أعد بناء الخدمة المقصودة؛ لا تمسح قاعدة البيانات لحل route مفقودة.

في هذا المستودع: `POST /api/v1/users` للتسجيل، و`POST /api/v1/login/access-token` للدخول، و`GET /api/v1/users/me` للهوية الحالية. المسارات canonical بلا trailing slash؛ قد تعيد النسخ المنتهية بـ slash تحويل 307. راجع OpenAPI الحالي بدلاً من افتراض أن كل مشروع FastAPI يستخدم نفس المسارات.

## Lab / تطبيق عملي

ابنِ جدول تشخيص يضم: backend متوقف، مسار خاطئ، method خاطئة، JSON ناقص، token غائب، وطلب صحيح. سجّل الأدلة من HTTP مباشرة. استخدم حساباً اختبارياً محلياً عند تجربة 201 → 200 → 200 للتسجيل والدخول والملف الشخصي، ثم احذف الحساب الاختباري فقط.

Acceptance criteria: capture status, method, URL and response media type; preserve the distinction between routing, validation, authentication and authorization; include a timeout; never commit passwords or bearer tokens.

## مراجعة ذاتية / Questions and answer notes

- هل نجاح health يثبت وجود login؟ لا؛ قد تكون صورة قديمة تحتوي health فقط.
- هل trailing slash تعني دائماً 404؟ لا؛ افحص سلوك التحويل الخاص بالخادم.
- هل CORS يحمي endpoint من عميل غير متصفح؟ ليس بديلاً عن تفويض الخادم.
- هل يمكن إعادة كل POST بعد timeout؟ لا؛ ربما نُفذ الطلب وفُقد الرد، فصمّم reconciliation أو idempotency.
- What is the first debugging artifact? The actual request method and URL paired with the actual response, not an assumption about which service handled it.
