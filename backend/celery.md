# Backend Engineering Mastery

**المرحلة:** Background Jobs & Task Queues

## 1. المشكلة التي نحلها أصلًا

تخيل أن لديك endpoint:

```http
POST /reports/generate
```

ويطلب المستخدم تقريرًا كبيرًا يحتاج إلى:

```text
قراءة بيانات من PostgreSQL
        ↓
حسابات كثيرة
        ↓
تجميع البيانات
        ↓
إنشاء PDF
        ↓
رفع الملف إلى Storage
        ↓
إرسال Email
```

قد تستغرق العملية 20 ثانية، أو دقيقتين، أو حتى 30 دقيقة. لو نفذت كل ذلك داخل FastAPI request، يصبح الـrequest مربوطًا بعمر المهمة:

```text
Client
   ↓
FastAPI
   ↓
Generate Report
   ↓
20 seconds
   ↓
Response
```

وهذا يسبب مشكلات في latency وtimeouts وworker utilization وscalability وreliability وتجربة المستخدم.

## 2. ماذا نريد بدلًا من ذلك؟

نريد أن تستقبل FastAPI الطلب وتضع Job في النظام ثم تعيد `202 Accepted`، بينما ينفذ worker العمل الحقيقي في الخلفية:

```text
Client
   ↓
FastAPI
   ↓
"تم استلام الطلب"
   ↓
202 Accepted

FastAPI
   ↓
RabbitMQ
   ↓
Celery Worker
   ↓
Heavy Task
```

```text
                 ┌───────────────┐
Client ────────→ │    FastAPI    │
                 └───────┬───────┘
                         │ publish job
                         ▼
                 ┌───────────────┐
                 │   RabbitMQ    │
                 └───────┬───────┘
                         │ consume
                         ▼
                 ┌───────────────┐
                 │ Celery Worker │
                 └───────┬───────┘
                         ▼
                    Heavy Task
```

FastAPI هنا لا تنفذ المهمة الثقيلة؛ إنها تستقبل الطلب وتضع Job في النظام. أما الـworker فينفذ العمل. توضح FastAPI أن `BackgroundTasks` مناسبة للمهام الصغيرة بعد إرسال الـresponse، بينما الحسابات الثقيلة التي يمكن تشغيلها خارج عملية FastAPI قد تستفيد من Celery مع RabbitMQ أو Redis؛ فهذا يسمح بتشغيل المهام عبر processes وservers متعددة.

## 3. الفرق بين BackgroundTasks وCelery

### FastAPI BackgroundTasks

المهمة ما زالت مرتبطة بعملية التطبيق نفسها:

```text
FastAPI Process
 ├── Request
 └── Background Task
```

مناسبة لإرسال email صغير أو كتابة log أو إرسال notification بسيط أو تنفيذ cleanup صغير.

### Celery

```text
FastAPI Process
      │
      ▼
 Message Broker
      │
      ▼
Worker Process 1
Worker Process 2
Worker Process 3
```

بهذا نفصل API serving عن task execution. وهذا هو التحول المعماري الحقيقي.

## 4. لا تحفظ كلمة Celery وحدها

لا تفكر في Celery على أنه مجرد background task library. الأدق أنه **Distributed Task Processing System**: نظام يتيح إرسال tasks إلى workers عبر message broker، مع دعم scheduling وretries وrouting وworkflows والمراقبة وغيرها. توثيق Celery الحالي يصفه كنظام لمعالجة العمل الموزع، والإصدار المستقر الموثق حاليًا هو 5.6 في سبتمبر 2026.

## 5. ما هو RabbitMQ؟

RabbitMQ هو **Message Broker**، أي وسيط رسائل. فكر فيه كصندوق بريد ضخم ومنظم، لكن بدل رسالة من شخص لشخص لدينا Job من Producer إلى Worker. مثال:

```text
GenerateReport(user_id=42)
```

يتم وضعها في messaging system.

## 6. أربعة أدوار يجب أن تحفظها

1. **Producer:** من ينتج الرسالة؛ في حالتنا FastAPI.
2. **Broker:** من يستقبل الرسالة ويديرها؛ في حالتنا RabbitMQ.
3. **Consumer / Worker:** من يأخذ الرسالة وينفذها؛ في حالتنا Celery Worker.
4. **Result Backend:** مكان اختياري لتخزين نتيجة وحالة الـtask؛ مثل Redis.

يمكن أن تكون المعمارية:

```text
FastAPI
   │ publish
   ▼
RabbitMQ
   │ deliver
   ▼
Celery Worker
   │ store result/status
   ▼
Redis
```

## 7. أهم تفرقة في الدرس: Broker vs Result Backend

لا تخلط بينهما:

- **Broker** يسأل: أين توجد الـjobs التي لم تُنفذ بعد؟ في مثالنا: RabbitMQ.
- **Result Backend** يسأل: ماذا حدث للـjob بعد تشغيلها؟ مثل `PENDING` و`STARTED` و`SUCCESS` و`FAILURE` و`RETRY`، ويمكنه تخزين result metadata.

في مشروعنا التعليمي سنستخدم RabbitMQ كـBroker وRedis كـResult Backend. Celery يدعم RabbitMQ وRedis كـbrokers، لكن RabbitMQ مصنف كـbroker مستقر ومدعوم حاليًا.

## 8. لماذا RabbitMQ أصلًا؟

افترض أن لديك FastAPI ويأتي 10,000 request في الدقيقة. لا نريد تنفيذ 10,000 عملية ثقيلة داخل API processes:

```text
10000 jobs
      ↓
RabbitMQ
      ↓
Workers
   ├── Worker 1
   ├── Worker 2
   ├── Worker 3
   └── Worker 4
```

RabbitMQ يشرح هذا كنمط **Work Queues / Competing Consumers**: عدة workers تشترك في queue وتتنافس على تنفيذ الرسائل.

## 9. أول Mental Model

```text
                    PRODUCER
                       │
                       ▼
                   RabbitMQ
                       │
                  ┌────┴────┐
                  │  Queue   │
                  └────┬────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Worker 1     Worker 2     Worker 3
          │            │            │
          ▼            ▼            ▼
       Execute      Execute      Execute
```

## 10. الـQueue

الـQueue هي المكان المنطقي الذي تنتظر فيه الرسائل دورها. مثلًا قد تحتوي `report_generation` على Job A وJob B وJob C وJob D وJob E، ثم توزعها workers كما يلي:

```text
Worker 1 → Job A
Worker 2 → Job B
Worker 3 → Job C
Worker 1 → Job D
Worker 2 → Job E
```

## 11. لماذا Queue؟

قد يكون الـProducer أسرع من الـWorkers:

```text
FastAPI: 100 jobs/sec
Workers: 20 jobs/sec
```

بدل انهيار النظام، تتراكم 80 jobs/sec في الـqueue. بذلك تصبح الـqueue **Shock Absorber** تمتص الاختلاف بين arrival rate وprocessing rate.

## 12. لكن انتبه

الـQueue ليست حلًا سحريًا. إذا كان الوارد 1,000 jobs/sec بينما المعالجة 100 jobs/sec، فستكبر الـqueue باستمرار. راقب:

- Queue depth
- Task age
- Worker throughput
- Failure rate

توضح RabbitMQ أن queue قد تمتلئ إذا كان كل العمال مشغولين؛ عندها تحتاج إلى مزيد من workers أو استراتيجية أخرى.

## 13. Producer لا ينتظر التنفيذ

عندما تنفذ:

```python
result = generate_report.delay(user_id)
```

فأنت لا تقول: «نفذ `generate_report` الآن وانتظر». بل ترسل رسالة تقول: «نفذ `generate_report` مع `user_id`».

## 14. `delay()` vs `apply_async()`

أبسط طريقة:

```python
generate_report.delay(user_id)
```

أما `apply_async()` فتسمح بإضافة options مثل `countdown` و`eta` و`expires` و`priority` و`routing`:

```python
generate_report.apply_async(
    args=[user_id],
)
```

توثيق Celery يعرّف `delay()` كاختصار لـ`apply_async()`، بينما `apply_async()` هو الخيار الذي يعطيك execution options إضافية.

## 15. أول Task لنا

```python
from celery import Celery

celery_app = Celery(
    "tasks",
    broker="amqp://guest:guest@localhost:5672//",
    backend="redis://localhost:6379/0",
)


@celery_app.task
def generate_report(user_id: int):
    print(f"Generating report for user {user_id}")

    return {
        "user_id": user_id,
        "status": "done",
    }
```

## 16. ماذا فعل `@celery_app.task`؟

حول الدالة `generate_report` إلى Celery Task. وبذلك أصبح Celery يعرف task name وarguments وexecution behavior وresult وretry behavior وrouting.

## 17. تشغيل Worker

بعد تعريف task، شغّل worker في process مستقل:

```bash
celery -A app.celery_app worker --loglevel=INFO
```

أي: استخدم Celery application الموجودة في `app.celery_app`، ثم شغّل worker وأظهر logs.

## 18. الآن FastAPI

```python
from fastapi import FastAPI
from app.tasks import generate_report

app = FastAPI()


@app.post("/reports/{user_id}")
async def create_report(user_id: int):
    task = generate_report.delay(user_id)

    return {
        "task_id": task.id,
        "status": "queued",
    }
```

## 19. ماذا يحدث بالضبط؟

عند إرسال `POST /reports/42` تنفذ FastAPI:

```python
generate_report.delay(42)
```

ثم تقوم Celery بعمل serialize للرسالة:

```json
{
  "task": "generate_report",
  "args": [42]
}
```

ثم تنتقل الرسالة عبر RabbitMQ إلى Celery Worker، الذي ينفذ `generate_report(42)`.

## 20. هذه ليست magic

تخيل الرسالة هكذا:

```json
{
  "task": "app.tasks.generate_report",
  "args": [42],
  "kwargs": {},
  "id": "uuid"
}
```

RabbitMQ ليس مطلوبًا منه معرفة Python function؛ فهو يتعامل مع Message. أما Celery worker فيفهم task name ويعرف أي Python function تمثلها.

## 21. RabbitMQ Architecture الأعمق

في RabbitMQ يوجد:

```text
Producer
   ↓
Exchange
   ↓
Binding / Routing
   ↓
Queue
   ↓
Consumer
```

وليس ببساطة `Producer → Queue`.

## 22. Exchange

الـExchange تستقبل الرسالة وتقرر إلى أي queue يجب أن تذهب. الأنواع الأهم هي `direct` و`topic` و`fanout` و`headers`، لكن Celery سيخفي عنك كثيرًا من التفاصيل في البداية. يكفي أن تفهم أن Celery ينشر task، ثم يوجّه RabbitMQ الرسالة إلى queue.

## 23. لماذا لا أتعامل مع RabbitMQ مباشرة؟

Celery يعطيك abstraction أعلى:

- Task
- Retry
- Scheduling
- Worker
- Concurrency
- Routing
- Workflow
- Result

وذلك بدل بناء كل هذه الوظائف بنفسك فوق AMQP.

## 24. Message Acknowledgment

تخيل أن RabbitMQ أرسل Job A إلى worker، لكن الـworker تعطل قبل أن ينتهي. نريد ألا تضيع المهمة.

## 25. Ack

الـworker يقول للـbroker `ACK`، أي: «استلمت الرسالة وأنجزت المعالجة، يمكنك اعتبارها processed». توضح RabbitMQ أن الرسالة غير المؤكدة يمكن إعادة تسليمها إذا انقطع الاتصال أو أُغلق channel قبل الـack؛ لذلك acknowledgements مهمة لسلامة المعالجة.

## 26. Early Acknowledgment

في الوضع التقليدي يمكن أن يتم الـack قبل تنفيذ المهمة:

```text
RabbitMQ
   ↓
Worker receives task
   ↓
ACK
   ↓
Worker executes
   ↓
CRASH
```

هنا قد تضيع المهمة لأن الـbroker تلقى `ACK`.

## 27. Late Acknowledgment

يمكن جعل الـack بعد تنفيذ task:

```text
RabbitMQ
   ↓
Worker receives
   ↓
Execute
   ↓
SUCCESS
   ↓
ACK
```

إذا مات worker أثناء التنفيذ، فلا يصل ACK، وبالتالي يمكن إعادة تسليم المهمة حسب إعدادات النظام. تدعم Celery ذلك عبر `acks_late`، وتوضح وثائقها أن المهام ذات late acknowledgment يجب أن تكون idempotent لأنها قد تنفذ أكثر من مرة إذا تعطل العامل.

## 28. مفهوم مهم: At-Least-Once Processing

معناه أن الأفضل إعادة تنفيذ المهمة على احتمال تكرارها بدل فقدانها. لكن هذا يعني أن المهمة قد تنفذ مرة أو مرتين أو أكثر؛ وهنا تظهر أهمية **Idempotency**.

## 29. ما هي Idempotency؟

هي عملية يمكن تكرارها دون أن تغير النتيجة النهائية أكثر من مرة. مثال سيئ:

```python
account.balance += 100
```

لو نفذت مرتين تصبح الزيادة `+200` بدل `+100`، لذا فهي ليست idempotent.

## 30. مثال Idempotent

بدل إنشاء payment جديد في كل مرة، استخدم `payment_id` فريدًا. إذا وصلت نفس الـtask مرة أخرى ووجدت أن `payment_id` موجود، تعرف أن العملية تمت بالفعل.

## 31. قاعدة ذهبية

إذا استخدمت `acks_late=True` فاسأل: ماذا يحدث لو نفذت المهمة مرتين؟ إذا كان النظام يفسد، فأنت لم تنته من تصميم المهمة.

## 32. Retry

تخيل أن worker يستدعي External API ويرجع له `503 Service Unavailable`. هل نعتبر المهمة فاشلة للأبد؟ غالبًا لا؛ نريد Retry.

## 33. Retry ليست «أعد كل شيء»

ميّز بين:

- **Transient Error:** مؤقت مثل timeout أو `503` أو temporary DB outage أو network error أو rate limit. غالبًا يستحق retry.
- **Permanent Error:** دائم مثل invalid email أو invalid user id أو bad input أو permission denied. إعادة المحاولة غالبًا لن تصلح المشكلة.

إذن: `Transient → Retry` و`Permanent → Fail`.

## 34. Celery Retry

```python
@app.task(bind=True)
def fetch_data(self, url):
    try:
        ...
    except TemporaryError as exc:
        raise self.retry(
            exc=exc,
            countdown=10,
        )
```

يوضح توثيق Celery أن `self.retry()` يرسل محاولة جديدة بنفس task ID ويسجل حالة task كـ`RETRY`.

## 35. Automatic Retry

```python
@app.task(
    autoretry_for=(TemporaryError,),
    retry_backoff=True,
)
def fetch_data(url):
    ...
```

تدعم Celery `autoretry_for` و`retry_backoff` و`retry_jitter`، وتستخدم exponential backoff مع jitter عندما يكون ذلك مفعّلًا.

## 36. لماذا Exponential Backoff؟

لا تجعل retries تتكرر كل 0.1 ثانية عندما يكون السيرفر الخارجي منهارًا. بدلًا من ذلك، اجعل الفواصل تتزايد:

```text
Attempt 1 → 1 sec
Attempt 2 → 2 sec
Attempt 3 → 4 sec
Attempt 4 → 8 sec
Attempt 5 → 16 sec
```

## 37. لماذا Jitter؟

إذا كان لديك 1,000 failed tasks وكلها تعيد المحاولة بعد 8 ثوانٍ، فسترسل 1,000 request في اللحظة نفسها. يجعل Jitter التوقيت غير متزامن.

## 38. Celery Configuration

مثال لإعداد يشبه بيئة الإنتاج:

```python
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    task_track_started=True,

    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

لا تحفظ الإعدادات كأنها وصفة تصلح لكل system؛ فلكل setting trade-off.

## 39. Prefetch

تخيل Worker 1 وWorker 2، وفي الـqueue:

```text
Job A = 60 sec
Job B = 60 sec
Job C = 1 sec
Job D = 1 sec
```

لو worker واحد أخذ A وB وC وD مقدمًا، فقد تنتظر jobs قصيرة خلف jobs طويلة.

## 40. Prefetch معناها

كم رسالة يمكن أن يحجزها worker مسبقًا من الـbroker قبل أن ينهي العمل الحالي؟ تعرّف Celery `worker_prefetch_multiplier` بأنه عدد الرسائل المحجوزة لكل concurrency slot، والافتراضي الحالي هو 4. عندما تكون المهام طويلة، توصي الوثائق غالبًا بقيمة 1 لتقليل احتجاز المهام مسبقًا.

## 41. مثال Prefetch

إذا كان `concurrency = 4` و`prefetch_multiplier = 4`، فقد يسمح الإطار بعدد كبير من الرسائل المحجوزة مسبقًا بالنسبة إلى الـworker. أما `prefetch_multiplier = 1` فيعطي سلوكًا أكثر تحفظًا للمهام الطويلة.

## 42. RabbitMQ Fair Dispatch

توضح RabbitMQ أن round-robin وحده ليس كافيًا إذا اختلفت مدة المهام. يمكن أن يجعل `prefetch = 1` الرسائل تنتقل إلى worker آخر عندما ينتهي العامل من مهمته السابقة.

## 43. CPU-bound vs I/O-bound: CPU-bound

أمثلة CPU-bound: image processing وvideo encoding وPDF rendering وcompression وML preprocessing والحسابات الثقيلة. هذه تستهلك CPU. توصي Celery افتراضيًا بـ`prefork` في أغلب الحالات، وهو مناسب خصوصًا للمهام التي تحتاج CPU.

## 44. I/O-bound

أمثلة I/O-bound: HTTP API calls وfile uploads وexternal services وdatabase-heavy work. غالبًا تنتظر هذه المهام I/O أكثر من CPU. يمكن أن يكون concurrency أعلى، لكن يجب قياس workload فعليًا.

## 45. لا تجعل Worker واحدًا يفعل كل شيء

تصميم سيئ:

```text
queue:
  send_email
  video_encode
  generate_pdf
  billing
  AI_embeddings

workers = same pool
```

قد تحجز `video_encode` worker لدقائق بينما تنتهي `send_email` في ثوانٍ.

## 46. Routing

يمكن فصل queues إلى `fast_tasks` و`heavy_tasks` و`emails` و`reports`، ثم تشغيل Fast Worker وHeavy Worker وEmail Worker وReport Worker. تدعم Celery routing مع queues منفصلة.

## 47. مثال Routing

```python
@app.task(queue="reports")
def generate_report(...):
    ...
```

ويمكن تشغيل worker خاص بـ`reports` وآخر خاص بـ`emails`.

## 48. لماذا Routing مهم؟

إذا كانت Reports ثقيلة على CPU وEmails قصيرة وتعتمد على I/O، فإن worker مشتركًا قد يجعل Reports تعطل Emails. أما فصل queues فيوفر Workload Isolation:

```text
             RabbitMQ
             /      \
      reports       emails
         ↓             ↓
   CPU workers     IO workers
```

## 49. Concurrency

إذا شغلت:

```bash
celery -A app.celery_app worker --loglevel=INFO --concurrency=4
```

فأنت تقول: 4 execution slots. لا يعني ذلك 4 tasks بأي workload دون حدود. إذا احتاجت كل task إلى 2 GB RAM وشغلت `concurrency=20` فقد تقتل machine نفسها.

## 50. Concurrency ليست «كلما زادت كان أفضل»

تعتمد Optimal Concurrency على CPU وRAM وI/O وtask duration وdatabase capacity وexternal API limits وworker model. تشير وثائق Celery إلى أن زيادة عدد عمليات workers لها نقطة يصبح بعدها الأداء أسوأ، وأن القيمة المناسبة تعتمد على workload.

## 51. Windows وCelery

لأن بيئتك الأساسية Windows، انتبه إلى أن Celery يعمل أفضل كبيئة تشغيل Linux/Unix من ناحية النموذج المعتاد للـprefork. توثيق Celery الحالي يذكر أن Windows يستخدم spawn بدل fork في prefork، وقد تحتاج عند المشاكل إلى `--pool=solo` أو `--pool=threads`. لذلك بيئة تعليمية مناسبة هي:

```text
Windows
   ↓
WSL2
   ↓
Linux
   ↓
Docker
```

## 52. FastAPI لا يجب أن تنتظر Celery

خطأ:

```python
task = generate_report.delay(user_id)
result = task.get()
return result
```

أنت بذلك تعود إلى Request ثم Wait ثم Wait ثم Wait، وتفسد فكرة background processing.

## 53. النمط الصحيح

```text
POST /reports
        ↓
queue task
        ↓
return 202

GET /tasks/{task_id}
```

## 54. لماذا HTTP 202؟

تعني `202 Accepted` منطقيًا أن الطلب استُقبل للمعالجة، لكن التنفيذ لم يكتمل بعد. وهذا مناسب جدًا لهذا النوع من APIs.

## 55. API Response

بعد enqueue قد تكون الاستجابة:

```json
{
  "task_id": "6d0...",
  "status": "PENDING"
}
```

ثم قد يرجع استعلام الحالة:

```json
{
  "task_id": "6d0...",
  "status": "STARTED"
}
```

وعند الاكتمال:

```json
{
  "task_id": "6d0...",
  "status": "SUCCESS",
  "result": {
    "report_id": 123
  }
}
```

## 56. FastAPI Status Endpoint

```python
from celery.result import AsyncResult


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.ready():
        response["result"] = result.result

    return response
```

## 57. Result Backend

بدون result backend قد تنفذ المهمة، لكن الاستعلام «what happened?» لا يكون كما تريد. مع Redis result backend يمكن حفظ metadata والنتائج. لكن انتبه: Result Backend ليس Queue.

## 58. أحيانًا لا نحتاج Result Backend

مهمة مثل `send_email` قد لا تحتاج إلى حفظ email body result في Redis إلى الأبد. يمكن تصميم task لتنفذ ثم تسجل أو تصدر event بحسب business needs.

## 59. لا تحفظ نتائج ضخمة في Result Backend

إذا كانت نتيجة task ملف فيديو حجمه 500 MB، فهذا غالبًا تصميم سيئ. الأفضل أن تنشئ worker الملف وترفعه إلى Object Storage ثم تعيد file ID أو URL، لا binary كاملًا كـtask result.

## 60. Task Payload Design

لا ترسل object ضخمًا أو DataFrame أو file bytes داخل الرسالة. أرسل IDs وreferences وpaths ومعاملات صغيرة، مثل:

```python
generate_report.delay(
    report_id=123,
    user_id=42,
)
```

ثم يقرأ worker ما يحتاجه.

## 61. لماذا؟

لأن task message تعبر الشبكة:

```text
FastAPI
   ↓ serialize
RabbitMQ
   ↓ deserialize
Worker
```

كلما زاد حجم الرسالة زادت serialization cost وnetwork cost وbroker memory وworker memory.

## 62. لا ترسل ORM objects

خطأ:

```python
generate_report.delay(user_model)
```

الأفضل:

```python
generate_report.delay(user_id)
```

لأن worker process مختلف، ولا ينبغي افتراض أن objects المرتبطة بعملية FastAPI قابلة للنقل أو الصلاحية بعد عبورها إلى process آخر.

## 63. Task Boundary

اعتبر task boundary أيضًا Process Boundary وNetwork Boundary. كل ما ترسله يجب أن يكون serializable وsmall وstable وexplicit.

## 64. Task Functions يجب أن تكون مستقلة

مثال جيد:

```python
@app.task
def generate_report(report_id: int):
    ...
```

ومثال سيئ أن تعتمد task على global FastAPI state؛ فالـworker ليس FastAPI process.

## 65. لا تعتمد على Request Object

لا ترسل `request` إلى Celery. استخرج ما تحتاجه مثل `user_id` و`tenant_id` و`locale` و`report_id` ثم أرسل هذه القيم.

## 66. Authentication Context

إذا كان request يحمل `Authorization: Bearer ...` فلا ترسل token نفسه إلى RabbitMQ لمجرد أن worker يحتاج context. الأفضل إرسال `user_id` و`tenant_id` وpermissions context أو business identifier، ثم يقرأ worker البيانات من المصدر وفق سياسة النظام.

## 67. Multi-Tenant Workers

في SaaS يكون `tenant_id` جزءًا مهمًا من task payload، مثل:

```python
generate_invoice.delay(
    tenant_id=15,
    invoice_id=983,
)
```

حتى لا ينفذ worker العملية في context خطأ.

## 68. Retry + Idempotency + Transactions

قد ينتج عن Retry وAt-least-once وdatabase transaction آثار جانبية مكررة:

```text
1. Create invoice
2. Send email
3. Task crashes after email
4. RabbitMQ redelivers
5. Send email again
```

لذلك تحتاج إلى تصميم يمنع duplication أو يجعلها مقبولة، باستخدام transaction وidempotency وoutbox وdeduplication حسب الحالة.

## 69. Idempotency Key

قبل تنفيذ side effect اسأل: Have I already processed this? يمكن استخدام `task_id` أو business key مثل `payment_id = 9876`. إذا عولجت العملية سابقًا فتوقف؛ وإلا نفّذها وسجّل اكتمالها.

## 70. Celery Task ID ليس دائمًا Business Idempotency Key

قد يختلف Celery task ID عن Payment ID أو Order ID. لذلك يجب أن تعتمد business idempotency على business identity لا على UUID الخاص برسالة النقل فقط.

## 71. Retry Architecture

```python
@app.task(
    autoretry_for=(TimeoutError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def sync_customer(customer_id: int):
    ...
```

المعنى: Timeout ثم Retry ثم Backoff ثم Jitter، وبحد أقصى 5 محاولات.

## 72. متى لا تستخدم Auto Retry؟

لا تستخدمه عادةً مع `ValidationError`. إذا كان `email = "not-an-email"` فلن يصبح صحيحًا بعد 5 محاولات.

## 73. Retry Budget

يجب أن يكون للـretry budget، مثل `max_retries = 5` أو time budget يساوي 10 دقائق. لأن retry forever قد ينتج Poison Task تعود باستمرار.

## 74. Poison Task

Bad input قد يجعل task تفشل ثم تعيد المحاولة ثم تفشل. استمرار ذلك يسبب Queue pollution وإهدار worker وتضخم logs والضغط على external service. عالجها بحد أقصى للمحاولات وسياسة فشل واضحة.

## 75. Dead Letter Thinking

في production systems قد تحتاج مكانًا للمهام التي فشلت نهائيًا أو تحتاج manual intervention:

```text
Normal Queue
    ↓
Retry
    ↓
Retry
    ↓
Max retries exceeded
    ↓
Failure handling / DLQ strategy
```

هذه خطوة لاحقة في RabbitMQ architecture، وليست شرطًا لأول تطبيق.

## 76. Task States

```text
PENDING
   ↓
STARTED
   ↓
SUCCESS
```

أو:

```text
PENDING
   ↓
STARTED
   ↓
FAILURE
```

أو:

```text
PENDING
   ↓
STARTED
   ↓
RETRY
   ↓
STARTED
   ↓
SUCCESS
```

تتيح Celery تتبع حالة `STARTED` عند تفعيل `task_track_started`.

## 77. لماذا STARTED مهم؟

إذا استغرقت المهمة 20 دقيقة وأظهر endpoint دائمًا `PENDING`، فقد لا تعرف هل وصلت للworker أم بدأ تنفيذها فعلًا. لذلك يفيد state tracking للمهام الطويلة.

## 78. Task Progress

يمكنك لاحقًا استخدام task metadata لإظهار تقدم مثل `progress = 65%` أو `Processing 650 / 1000 files`. لكن لا تجعل database/result backend يتلقى آلاف التحديثات في الثانية لمجرد progress bar.

## 79. Polling

أبسط طريقة للـfrontend:

```text
POST /reports
   ↓
task_id
   ↓
GET /tasks/{task_id} every 2 seconds
   ↓
SUCCESS
```

## 80. مشكلة Polling

إذا كان لديك مليون client وكل client ينفذ `GET /tasks/id` كل ثانية، فقد صنعت load جديدًا. الحلول الأكبر: WebSocket أو Server-Sent Events أو push notifications أو event-driven UI.

## 81. Scheduled Tasks

Celery لا تقتصر على `run now`. يمكنك تشغيل لاحقًا:

```python
task.apply_async(
    args=[42],
    countdown=60,
)
```

أي بعد دقيقة تقريبًا، أو باستخدام `eta=...` لوقت محدد. يحذر التوثيق من استخدام countdown/eta بكميات كبيرة لفترات بعيدة؛ فقد تُحجز المهام في ذاكرة worker حتى موعدها، ومع RabbitMQ توجد اعتبارات acknowledgement timeout. للجدولة طويلة الأجل توجد أدوات مثل Celery Beat/schedulers.

## 82. Celery Beat

إذا أردت `cleanup_old_reports()` كل يوم الساعة 2:00 AM، استخدم Celery Beat. Beat لا ينفذ المهمة الثقيلة بنفسه، بل دوره scheduler يطلق task في أوقات محددة:

```text
Celery Beat
     │
     ▼
RabbitMQ
     │
     ▼
Worker
```

## 83. لا تشغل أكثر من Beat Scheduler لنفس schedule بدون تصميم لذلك

إذا قرر Beat A وBeat B إطلاق المهمة نفسها، قد تحصل على duplicate execution. تنبه وثائق Celery إلى ضرورة وجود scheduler واحد فقط لكل schedule في هذا النوع من الإعدادات.

## 84. Workflow

يمكنك بناء workflows مثل:

```text
Task A
   ↓
Task B
   ↓
Task C
```

أو تنفيذ عدة tasks بالتوازي ثم جمع النتائج:

```text
Task A ─┐
Task B ─┼→ Final Task
Task C ─┘
```

## 85. Chain

مثال:

```text
download_file
      ↓
process_file
      ↓
upload_result
      ↓
notify_user
```

توفر Celery Canvas primitives مثل `chain` و`group` و`chord` لبناء workflows موزعة.

## 86. Group

تشغل مجموعة مستقلة بالتوازي، مثل معالجة 1,000 صورة وتقسيمها إلى tasks منفصلة بدل تنفيذها تباعًا في task واحدة.

## 87. Chord

إذا أردت تنفيذ A وB وC وD بالتوازي ثم تشغيل Final Aggregation Task بعد انتهائها جميعًا، فهذا يسمى Chord. تعرف وثائق Celery الـchord بأنه task لا يبدأ إلا بعد انتهاء جميع المهام داخل الـgroup.

## 88. مثال واقعي

تقرير Sales شهري قد ينفذ:

```text
Fetch region A ─┐
Fetch region B ─┤
Fetch region C ─┼→ Aggregate → Generate PDF → Upload → Email
Fetch region D ─┘
```

يمكن تحويله إلى workflow موزع بدل task واحدة عملاقة.

## 89. لا تجعل Task تستدعي `.get()` على Task أخرى

خطأ:

```python
@app.task
def task_a():
    result = task_b.delay()
    return result.get()
```

لأن worker يصبح مشغولًا بالانتظار. تحذر Celery من الانتظار المتزامن على نتائج subtasks داخل task لأنه يحجز worker process بلا داعٍ. الأفضل استخدام `chain` أو `group` أو `chord` أو callbacks.

## 90. API Design الصحيح

بدل أن ينتظر `POST /generate-report` التقرير 60 ثانية ثم يعيد `200 OK`، اجعل `POST /reports` يعيد `202 Accepted` و`task_id` وحالة `PENDING`، ثم استعلم عبر `GET /tasks/{task_id}`.

## 91. لماذا هذا أفضل؟

تصبح API سريعة وresponsive وdecoupled وقابلة للتوسع، ويكون الـworker مستقلًا.

## 92. Task Timeout

قد تعلق مهمة لأن External API لا يرد. لا تريد أن يبقى worker slot مشغولًا إلى الأبد، لذا ضع timeouts على الخدمات التي تستدعيها المهمة:

```python
requests.get(
    url,
    timeout=10,
)
```

## 93. لا تعتمد على Celery وحده لعمل timeout

إذا كانت task تحتوي HTTP call، تحتاج أيضًا إلى HTTP timeout. فـCelery task timeout وsocket timeout ليسا المشكلة نفسها.

## 94. Time Limits

توفر Celery task time limits، لكن استخدامها يحتاج فهمًا للـpool والـsignals وطبيعة العملية. قد توقف أو تنهي task عند تجاوز الحد وفق الإعداد، لكنها ليست بديلًا عن timeout صحيح للمكتبات الخارجية.

## 95. Worker Memory

إذا عالجت المهمة DataFrame ضخمًا، فقد يبقى worker process مستهلكًا للذاكرة. توفر Celery خيارات لإدارة workers مثل max tasks per child وإعادة إنشاء worker child بعد عدد معين من المهام في بعض السيناريوهات.

## 96. Observability

إذا كان لديك 100,000 tasks فلا يكفي أن تقول «النظام شغال». راقب queue depth وtask latency وexecution time وsuccess rate وfailure rate وretry rate وworker utilization وtask age.

## 97. أهم Metrics

- Tasks Submitted
- Tasks Started
- Tasks Succeeded
- Tasks Failed
- Tasks Retried
- Average Runtime
- P95 Runtime
- Queue Wait Time
- Queue Depth

## 98. Queue Wait Time

قد يستغرق التنفيذ ثانيتين، لكنه ينتظر 90 ثانية قبل أن يبدأ؛ فيشعر المستخدم بـ92 ثانية. لذلك `Queue latency` لا تساوي `Task execution latency`.

## 99. Capacity Planning

إذا كان الوارد 100 tasks/sec ومتوسط وقت المهمة ثانيتين، فأنت تحتاج عددًا كافيًا من execution slots حتى لا يتضخم backlog. هذه بداية التفكير في Throughput.

## 100. Worker Scaling

إذا ارتفع queue depth من 100 إلى 200 إلى 500 إلى 1,000 فقد تحتاج إلى زيادة worker count أو concurrency. لكن concurrency قد يضغط CPU وRAM وDatabase وExternal APIs، لذا يجب أن يعتمد scaling على bottleneck.

## 101. Horizontal Scaling

بدل worker واحد، يمكن تشغيل عدة workers تشترك في queue:

```text
Worker 1
Worker 2
Worker 3
Worker 4
Worker 5
```

يتولى RabbitMQ توزيع الرسائل بينهم، مع تأثيرات prefetch وacknowledgements على عدالة التوزيع.

## 102. الاستفادة الأكبر

يمكن توسيع FastAPI instances والـworkers كلٌّ بشكل مستقل:

```text
API 1 ─┐
API 2 ─┼→ RabbitMQ → Worker 1
API 3 ─┘             Worker 2
                     Worker 3
                     Worker 4
                     Worker 5
```

وهذا من أهم أسباب استخدام queues.

## 103. API Scaling vs Worker Scaling

إذا كان API CPU = 30% والـWorkers CPU = 95%، فالمشكلة في worker capacity؛ زِد workers بدل زيادة FastAPI instances.

## 104. والعكس

إذا كانت FastAPI overloaded والـWorkers idle، فلا تزِد workers؛ زِد API instances. هذه هي فكرة Independent Scaling.

## 105. Security

لا تفتح RabbitMQ للـInternet عشوائيًا. معمارية نموذجية:

```text
Internet
   ↓
Load Balancer
   ↓
FastAPI
   ├── RabbitMQ
   └── Redis
```

ضع RabbitMQ وRedis داخل private network قدر الإمكان.

## 106. Credentials

لا تضع credentials مثل `broker="amqp://guest:guest@..."` في production. استخدم `RABBITMQ_URL` و`CELERY_BROKER_URL` و`CELERY_RESULT_BACKEND` من environment/config system.

## 107. Serialization

في الإنتاج لا ترسل pickle everything إذا لم تكن تحتاج ذلك. الأفضل استخدام JSON:

```python
task_serializer="json"
result_serializer="json"
accept_content=["json"]
```

## 108. لماذا JSON؟

لأنه explicit وportable وinspectable وlanguage-independent. لكن تذكّر أنه يفرض قيودًا على أنواع البيانات.

## 109. Task Input Contract

ضع task contract واضحًا. بدل `def task(data)` استخدم معاملات صريحة مثل:

```python
def generate_invoice(
    tenant_id: int,
    invoice_id: int,
):
    ...
```

فالمعاملات الواضحة أفضل للاختبار والمراقبة والتطور.

## 110. Database Connections داخل Workers

لا تفترض أن connection التي أنشأتها FastAPI يمكن أن يعاد استخدامها بواسطة Celery worker. غالبًا لكل FastAPI process وCelery worker process lifecycle خاص لإدارة database connections.

## 111. ORM Session

داخل task أنشئ session وأغلقها بطريقة صحيحة:

```python
@app.task
def generate_report(report_id):
    session = create_session()

    try:
        ...
    finally:
        session.close()
```

أو استخدم dependency/resource pattern مناسبًا للـworker. المهم ألا تستخدم session مرتبطة بعمر FastAPI request.

## 112. Task Transaction

قد تحتاج المهمة إلى transaction:

```text
BEGIN
   ↓
load
   ↓
update
   ↓
COMMIT
   ↓
external side effect
```

ترتيب العمليات مهم.

## 113. مثال مشكلة

إذا حدث DB update ثم أُرسل email ثم تعطّل worker، فقد تعيد المحاولة DB update وemail. لذلك نحتاج transaction وidempotency وoutbox وdeduplication في الأنظمة الأكبر.

## 114. Outbox Pattern

في architecture متقدمة:

```text
DB Transaction
 ├── update business data
 └── insert outbox event
        ↓
    Publisher
        ↓
    RabbitMQ
```

هذا يقلل مشكلة أن قاعدة البيانات تم اعتمادها لكن الرسالة لم تُنشر.

## 115. Celery + RabbitMQ ليس Event Sourcing

لا تخلط بين Task Queue وEvent Log. RabbitMQ + Celery تقول: «نفذ هذا العمل». أما Event Sourcing فيسجل: «هذا ما حدث في النظام». قد يستخدمان transport متشابهًا لكن semantics مختلفة.

## 116. Task Queue vs Pub/Sub

في Work Queue عادة ينفذ Job واحد worker. أما في pub/sub فقد تصل Message إلى عدة consumers. تدعم RabbitMQ كلا النمطين، لكن Celery task queue مبنية عادة على worker competition.

## 117. عمليًا: متى تستخدم Celery؟

مناسب لـPDF generation وimage processing وvideo processing وlarge imports وdata exports وETL وAI preprocessing وembeddings وbatch operations وlong-running API integrations وemail campaigns وscheduled maintenance.

## 118. متى لا تستخدمه؟

إذا كانت المهمة 100ms ولا تحتاج retries أو durable work أو independent workers أو scaling أو scheduling، فقد يكون Celery overkill.

## 119. لا تستخدم Queue لمجرد أنها موجودة

لكل abstraction تكلفة: RabbitMQ وCelery وworkers وmonitoring وdeployment وretries وserialization وfailure modes. الأنظمة الموزعة تحل مشكلات بإدخال مشكلات أخرى؛ والهندسة هي اختيار trade-offs المناسبة.

## 120. أول تشغيل عملي

تثبيت Celery:

```bash
python -m pip install celery
```

ولو تستخدم Redis كـresult backend:

```bash
python -m pip install redis
```

## 121. تشغيل RabbitMQ

في التطوير يمكن تشغيل RabbitMQ عبر Docker:

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:4-management
```

بعدها:

```text
AMQP: localhost:5672
Management UI: localhost:15672
```

توثق RabbitMQ حاليًا tutorial وwork-queue examples على RabbitMQ 4.x، كما توفر واجهات إدارة في صور/توزيعات مناسبة للاستخدام المحلي.

## 122. Project Structure

```text
backend-mastery/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── celery_app.py
│   ├── tasks.py
│   └── services/
│       └── reports.py
├── tests/
│   └── test_tasks.py
├── requirements.txt
└── .env
```

## 123. `celery_app.py`

```python
from celery import Celery

celery_app = Celery(
    "backend_mastery",
    broker="amqp://guest:guest@localhost:5672//",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

## 124. `tasks.py`

```python
import time

from app.celery_app import celery_app


@celery_app.task
def generate_report(user_id: int) -> dict:
    print(f"Starting report for user={user_id}")

    time.sleep(10)

    print(f"Finished report for user={user_id}")

    return {
        "user_id": user_id,
        "report_id": f"report-{user_id}",
        "status": "completed",
    }
```

لاحظ أن المهمة متعمدة أن تكون sync، لأن Celery Worker ليس هو نفسه FastAPI async event loop، وسنتناول async workers/concurrency بتفصيل أكبر لاحقًا.

## 125. `main.py`

```python
from celery.result import AsyncResult
from fastapi import FastAPI

from app.celery_app import celery_app
from app.tasks import generate_report

app = FastAPI()


@app.post("/reports/{user_id}", status_code=202)
async def create_report(user_id: int):
    task = generate_report.delay(user_id)

    return {
        "task_id": task.id,
        "status": "PENDING",
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.ready():
        response["result"] = result.result

    return response
```

## 126. تشغيل FastAPI

```bash
fastapi dev app/main.py
```

أو بالطريقة التي تستخدمها في مشروعك.

## 127. تشغيل Worker

في terminal ثانية:

```bash
celery -A app.celery_app worker --loglevel=INFO
```

## 128. الآن جرّب

أرسل `POST /reports/42`. ستأخذ:

```json
{
  "task_id": "....",
  "status": "PENDING"
}
```

انتقل للـworker وستجد `Received task...` ثم `Starting report...`. بعد 10 ثوانٍ ستجد `Finished report...`. ثم نفذ `GET /tasks/{task_id}` وستجد:

```json
{
  "task_id": "...",
  "status": "SUCCESS",
  "result": {
    "user_id": 42,
    "report_id": "report-42",
    "status": "completed"
  }
}
```

## 129. افهم ما حدث على مستوى العمليات

أصبح عندك:

```text
Process 1: FastAPI
Process 2: Celery Worker
Process 3: RabbitMQ
Process 4: Redis
```

هذا Distributed Architecture حتى لو كانت كلها على نفس جهازك.

## 130. Exercise 1 — أثبت أن FastAPI لا تنتظر

اجعل task تنفذ `time.sleep(20)`، ثم اطلب `POST /reports/42`. يجب أن يرجع response فورًا تقريبًا. اكتب في `EXPERIMENTS.md` الوقت لكل من API response time وTask execution time.

## 131. Exercise 2 — أوقف Worker

شغّل FastAPI وRabbitMQ، وأوقف Worker. أرسل `POST /reports/42`. قد تصل المهمة إلى broker وتنتظر worker حسب حالة broker/queue. شغّل worker وراقب ما يحدث. الهدف رؤية Decoupling.

## 132. Exercise 3 — شغّل عاملين

Terminal 1:

```bash
celery -A app.celery_app worker --loglevel=INFO --hostname=worker1@%h
```

Terminal 2:

```bash
celery -A app.celery_app worker --loglevel=INFO --hostname=worker2@%h
```

أرسل 20 tasks وراقب التوزيع.

## 133. Exercise 4 — Long Tasks

اجعل Job A وJob B تستغرقان 30 ثانية، وJob C وJob D تستغرقان ثانية واحدة. جرّب `prefetch_multiplier = 4` ثم `prefetch_multiplier = 1`. راقب أي worker حصل على كل task واكتب تحليلًا في `PREFETCH_ANALYSIS.md`.

## 134. Exercise 5 — Worker Crash

أنشئ task:

```python
@app.task
def unstable_task():
    import os
    os._exit(1)
```

شغّلها مع `acks_late` وراقب ما يحدث للمهمة. الهدف رؤية الفرق بين “message received” و“message successfully acknowledged”.

## 135. Exercise 6 — Retry

أنشئ attempts واجعل task تفشل مرتين ثم تنجح، مثلًا باستخدام state خارجي بسيط أثناء التجربة. المطلوب:

```text
attempt 1 → FAILURE
attempt 2 → RETRY
attempt 3 → SUCCESS
```

ثم استخدم `retry_backoff=True` وشاهد فرق التوقيت.

## 136. Exercise 7 — Permanent Failure

أنشئ `invalid_user_id` واجعلها `ValueError`، وتأكد أن هذا الخطأ لا يعامل كـtransient retry. اكتب لماذا.

## 137. Exercise 8 — Idempotency

نفذ `create_invoice(order_id)` بدون idempotency ونفذها مرتين؛ راقب وجود فاتورتين. ثم أصلحها باستخدام unique `order_id` أو idempotency record، وأثبت أن تنفيذين ينتجان business effect واحدًا.

## 138. Exercise 9 — Queue Isolation

أنشئ queues باسم `reports` و`emails`. وجّه `generate_report` إلى `reports` و`send_email` إلى `emails`، ثم شغّل report workers وemail workers. اختبر أن overload التقارير لا يمنع email pipeline من العمل.

## 139. Exercise 10 — Task Status API

أضف `GET /tasks/{task_id}` واختبر الحالات: `PENDING` و`STARTED` و`SUCCESS` و`FAILURE` و`RETRY`.

## 140. Exercise 11 — Expiration

جرّب:

```python
task.apply_async(
    args=[42],
    countdown=10,
    expires=5,
)
```

فكر: task scheduled لكن expiration يحدث أولًا. راقب الحالة. تدعم Celery `expires` بحيث لا تنفذ المهمة بعد انتهاء صلاحيتها وتسجلها كـ`REVOKED`.

## 141. Exercise 12 — Queue Backlog

أنشئ 1,000 heavy tasks وشغّل worker واحدًا وراقب queue depth، ثم شغّل 3 workers ثم 5 workers وقارن processing time.

## 142. Exercise 13 — CPU Worker

أنشئ task حسابية مثل `cpu_heavy_work(n)`، وقارن `concurrency = 1` مع 2 و4 و8. لا تفترض أن 8 أفضل دائمًا.

## 143. Exercise 14 — Failure Storm

اجعل External API وهميًا يفشل مع 100 tasks تستخدم `autoretry_for` و`retry_backoff` و`retry_jitter`. راقب نمط retry ثم عطّل jitter وقارن. هنا سترى عمليًا لماذا jitter موجود.

## 144. Exercise 15 — Chain

نفذ `download → process → upload` باستخدام Celery Canvas chain، بحيث تنتقل نتيجة Task A إلى Task B ثم Task C.

## 145. Exercise 16 — Group

قسّم 100 image jobs إلى group وشغّلها بالتوازي. قارن زمن التنفيذ مع one giant task.

## 146. Exercise 17 — Chord

نفذ معالجة متوازية لأربعة ملفات ثم aggregate. استخدم `group + callback`، أي group ثم callback.

## 147. Exercise 18 — Worker Crash Simulation

شغّل task runtime مدتها 30 ثانية ثم اقتل worker بعد 10 ثوانٍ. لاحظ ما حدث: هل أُكدت الرسالة؟ هل أُعيد تسليمها؟ هل حدث business effect مرتين؟ اكتب `WORKER_CRASH_ANALYSIS.md`.

## 148. Exercise 19 — Duplicate Effects

أنشئ `send_welcome_email` يمكن أن تنفذ مرتين. لاحظ duplicate emails ثم أضف idempotency key وأثبت أن تنفيذين ينتجان إرسال email واحدًا أو استخدم استراتيجية deduplication مناسبة.

## 149. Exercise 20 — Production-Like Report System

ابنِ Report Processing Platform:

- API: أنشئ report record في DB، enqueue task، ثم أعد `task_id`.
- Worker: اقرأ report، وعلّمه `PROCESSING`، وأنشئ التقرير، واحفظ الملف، وعلّمه `COMPLETED`، واحفظ output location.
- عند الفشل: علّمه `FAILED`.

## 150. Production Architecture

```text
                         Client
                            │
                            ▼
                       FastAPI API
                            │
                  ┌─────────┴─────────┐
                  │                   │
                  ▼                   ▼
              PostgreSQL           RabbitMQ
                  │                   │
                  │                   ▼
                  │              Celery Workers
                  │               /     |      \
                  │              /      |       \
                  │             ▼       ▼        ▼
                  │          Reports  Emails   Exports
                  │
                  ▼
              Redis (Result / State)
```

## 151. Database Model

مثال جدول `reports`:

```text
reports
-------
id
user_id
status
created_at
started_at
completed_at
error_message
output_url
```

الحالات: `PENDING` و`PROCESSING` و`COMPLETED` و`FAILED`. لا تعتمد فقط على Celery state؛ يجب أن تكون business state في domain model إذا كان النظام يحتاجها.

## 152. لماذا نخزن Business State في PostgreSQL أيضًا؟

Celery result backend جزء infrastructure. لكن المستخدم قد يريد `GET /reports/123` بعد وقت طويل. لذلك خزّن Report record في database؛ يجعل ذلك business lifecycle مستقلًا عن transport.

## 153. لا تجعل Database تعتمد على Celery Task State فقط

إذا خزنت `PENDING/SUCCESS` فقط في Redis ثم انتهت صلاحية النتيجة، فستسأل: «Where is my report?» الأفضل:

```text
PostgreSQL = business truth
Celery = execution orchestration
Redis = transient state/result
RabbitMQ = transport
```

## 154. هذا Architecture مهم جدًا

لكل component دور:

- PostgreSQL → business data
- RabbitMQ → message transport
- Celery → task execution
- Redis → result/cache/temporary coordination
- FastAPI → HTTP interface

لا تجعل كل component يفعل كل شيء.

## 155. ماذا يحدث لو RabbitMQ وقع؟

إذا كان RabbitMQ هو broker الأساسي، فقد لا تستطيع enqueue task. تحتاج failure response وretry policy وobservability على مستوى producer أيضًا. تدعم Celery retry لعملية إرسال الرسائل عند connection failure ويمكن ضبط السياسة.

## 156. ماذا يحدث لو Worker وقع؟

قد يكون RabbitMQ متاحًا والـWorker متوقفًا؛ عندها تنتظر المهام. عندما يعود worker يستمر العمل وفق acknowledgement/retry semantics.

## 157. ماذا يحدث لو Redis Result Backend وقع؟

إذا كان RabbitMQ والـWorker يعملان لكن Redis غير متاح، فقد تستمر task في التنفيذ بينما تواجه status/result retrieval مشكلة بحسب التصميم.

## 158. ماذا يحدث لو Database وقعت؟

قد تفشل task. ربما تحتاج إلى retry للأخطاء المؤقتة في DB، لكن ليس إلى retry غير محدود. ميّز transient DB error عن invalid business state.

## 159. Failure Matrix

| Dependency | Failure | Expected behavior |
| --- | --- | --- |
| RabbitMQ | Enqueue unavailable | API returns controlled error/retry |
| Worker | Crash | Task redelivery according to ack policy |
| Redis | Result unavailable | Execution may continue but status query may degrade |
| PostgreSQL | Transient outage | Retry selected tasks |
| External API | 503 | Exponential backoff |
| External API | Invalid request | No retry |

## 160. Queue Depth كإشارة للـScaling

إذا زاد queue depth بمرور الوقت، مثل 100 ثم 300 ثم 700 ثم 1,500 ثم 3,000، فهذا يعني arrival rate > processing rate، وليس بالضرورة أن RabbitMQ بطيء. قد تكون المشكلة في worker capacity أو task duration أو downstream dependency.

## 161. Task Duration Distribution

لا تنظر فقط إلى average task time. قد تكون 90% من المهام ثانية واحدة و10% خمس دقائق، فيظهر tail latency. استخدم P50 وP95 وP99.

## 162. Task Priority

يمكن لبعض brokers/routing configurations دعم task priority. توفر Celery priority options، لكن تأثيرها مرتبط بالـbroker وprefetch وإعداداته. تحذر الوثائق من أن prefetch قد يجعل التنفيذ الأولي يبدو خارج ترتيب الأولوية؛ لذلك priority ليست magic queue ordering.

## 163. Queue Per Workload vs Priority

بدل queue واحدة و`priority=high`، قد يكون أبسط أن تستخدم queues مثل `critical` و`normal` و`bulk` مع workers منفصلة. هذا يعطي Isolation.

## 164. Bulk Processing

إذا كان لديك مليون record فلا تجعل كل record task منفصلة بالضرورة، لأنك قد تصنع مليون message. ربما يكون الأفضل batching بمجموعات من 1,000، لكن حجم batch نفسه trade-off.

## 165. Fan-Out/Fan-In

```text
One Request
    ↓
100 Tasks       ← Fan-Out
    ↓
100 Results
    ↓
1 Aggregator    ← Fan-In
```

يمكن لـCelery `group + chord` التعبير عن هذا النوع من workflows.

## 166. لا تجعل Task ضخمة جدًا

قد تكون task مدتها 8 ساعات مشكلة. أحيانًا الأفضل تقسيمها إلى tasks مستقلة، لكن لا تقسّم المهمة إلى آلاف القطع دون داعٍ؛ فكل message لها serialization وbroker overhead وscheduling وack وresult.

## 167. أين تستخدم Celery في AI Backend؟

إذا رفع المستخدم 500 documents، يمكن أن تنشئ FastAPI ingestion job ثم تنفذ workers استخراج النص وchunking وإنشاء embeddings وتخزين vectors، ثم final aggregation. هذه architecture مهمة في RAG Backend.

## 168. مثال AI Pipeline

```text
Upload PDF
    ↓
FastAPI
    ↓
RabbitMQ
    ↓
extract_text
    ↓
chunk_documents
    ↓
generate_embeddings
    ↓
store_vectors
    ↓
mark_ingestion_complete
```

يمكن أن يكون كل stage task أو مجموعة tasks.

## 169. لماذا هذا مهم؟

قد يكون embedding generation بطيئًا ومكلفًا ومقيدًا بمعدل الاستخدام وقابلًا لإعادة المحاولة وقابلًا للتوازي؛ وهذه خصائص تجعل task queues مناسبة.

## 170. لكن لا ترسل document نفسه داخل RabbitMQ

بدل PDF bytes، خزّن الملف في S3/object storage ثم أرسل `document_id` و`storage_key` و`tenant_id`. يجلب worker الملف. هذه architecture أفضل من وضع blobs ضخمة داخل message.

## 171. RabbitMQ كـTraffic Buffer

إذا كان AI API يستقبل 1,000 uploads/sec بينما embedding service يسمح بـ100/sec، تصبح queue buffer. لكن إذا استمر الوارد 1,000/sec إلى الأبد، سينفجر backlog. queues تعالج bursts، لا نقص القدرة الدائم.

## 172. Backpressure

Backpressure تعني أن النظام يخبر upstream بشكل غير مباشر أن downstream لا يستطيع معالجة كل هذه السرعة. الحلول تشمل queueing وrate limiting وload shedding وbatching وscaling وpriority.

## 173. Queue Length ليس Metric فقط

يمكن أن يكون control signal، مثل `Queue > 1000 → scale workers` و`Queue < 100 → scale down`. هذه بداية autoscaling.

## 174. Autoscaling في Kubernetes لاحقًا

```text
RabbitMQ queue depth
      ↓
Autoscaler
      ↓
Worker replicas
```

مثال: 2 workers ثم 1,000 queued tasks، فترفع إلى 8 workers، وبعد هبوط الحمل تخفضها 8 ثم 4 ثم 2.

## 175. Monitoring

لدى Celery monitoring ecosystem، ولدى RabbitMQ management/monitoring capabilities. راقب workers وtasks وqueues وrates وfailures. في البداية يمكنك استخدام logs وRabbitMQ Management UI، ثم تضيف metrics/tracing لاحقًا.

## 176. Logging الصحيح

لا تسجل object ضخمًا. سجّل `task_id` و`task_name` و`tenant_id` و`resource_id` و`attempt` و`duration` و`status`. مثال:

```python
logger.info(
    "report_generation_started",
    extra={
        "report_id": report_id,
        "task_id": self.request.id,
    },
)
```

## 177. Correlation ID

اربط request ID بـtask ID ثم worker logs وdatabase record:

```text
request_id = abc
   ↓
task_id = xyz
   ↓
worker logs
   ↓
database record
```

حتى تستطيع تتبع رحلة العملية كاملة. هذا أساس مهم للـdistributed tracing.

## 178. Task Name

اجعل أسماء tasks واضحة مثل `reports.generate` و`reports.cleanup` و`emails.send` و`users.sync` و`documents.embed` بدل `task1` أو `do_work`؛ فاسم task يظهر في logs وmonitoring وrouting وdebugging.

## 179. Task Versioning

في distributed deployment قد تعمل Worker version A وWorker version B، وقد تحتوي queue على messages من الإصدار السابق. اجعل task payloads backward-compatible قدر الإمكان، مثل:

```json
{
  "version": 1,
  "report_id": 123
}
```

ثم مستقبلًا:

```json
{
  "version": 2,
  "report_id": 123,
  "locale": "ar"
}
```

## 180. Deployment

في Production لا تشغل FastAPI وCelery وRabbitMQ وRedis داخل process واحد. عادة تكون API containers وWorker containers وRabbitMQ وRedis وPostgreSQL، ولكل واحد lifecycle واضح.

## 181. مثال Deployment

```text
                Load Balancer
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          API 1                API 2
             │                   │
             └─────────┬─────────┘
                       ▼
                   RabbitMQ
                 /     |     \
                ▼      ▼      ▼
           Worker 1 Worker 2 Worker 3
                │      │      │
                └──────┼──────┘
                       ▼
                   PostgreSQL
                       │
                       ▼
                     Redis
```

## 182. Worker Types

في مشروع كبير قد تعمل `worker-reports` و`worker-emails` و`worker-ai` و`worker-maintenance`. لكل worker queues محددة وconcurrency وresources خاصة.

## 183. Resource Isolation

مثال:

```text
AI workers:      8 CPU, 16 GB RAM
Email workers:   1 CPU, 1 GB RAM
Report workers:  4 CPU, 8 GB RAM
```

هذا أفضل من worker pool موحد لكل الأنواع.

## 184. RabbitMQ Durability

تدعم RabbitMQ durable queues وpersistent messages لتصميم الرسائل بحيث تبقى عبر restart المناسب. لكن durability ليست ضمانًا بأن task لن تتكرر أو أن downstream side effect آمن. يوضح Work Queue tutorial استخدام durable queues وmessage persistence مع acknowledgements.

```text
Durable ≠ Idempotent
```

## 185. Publisher Confirms

يحتاج producer أيضًا إلى معرفة: هل استلم broker الرسالة؟ توفر RabbitMQ Publisher Confirms كآلية feedback للناشر، بجانب consumer acknowledgements على جهة المستهلك. تصبح هذه مهمة في الأنظمة التي تحتاج guarantees أقوى.

## 186. Delivery Guarantees

حدد ما تحتاجه:

- At-most-once
- At-least-once
- Exactly-once

## 187. At-Most-Once

المهمة تنفذ صفر أو مرة واحدة. الميزة: لا duplicates. العيب: قد يضيع العمل.

## 188. At-Least-Once

المهمة تنفذ مرة أو أكثر. الميزة: احتمال أقل لفقد العمل. العيب: احتمال التكرار؛ لذلك نحتاج Idempotency.

## 189. Exactly-Once

هذا تعبير خطير. تتحدث أنظمة كثيرة عن exactly-once processing، لكن المهم على مستوى business effect هو Exactly-once business effect، وهو أصعب بكثير من message delivered once.

## 190. مثال الدفع

إذا استدعى worker Stripe API بنجاح ثم تعطل قبل تسجيل نجاح task، فقد تحدث retry وتُخصم الدفعة مرة أخرى. لا تنقذك RabbitMQ وحدها؛ تحتاج idempotency key في payment provider أو business layer.

```text
Messaging semantics ≠ Business semantics
```

## 191. أهم أسئلة Production قبل إطلاق Celery

اسأل:

- What happens if the worker crashes?
- What happens if RabbitMQ crashes?
- What happens if PostgreSQL crashes?
- What happens if Redis crashes?
- What happens if task runs twice?
- What happens if task retries 5 times?
- What happens if task never succeeds?
- What happens if queue grows forever?
- What happens if one task takes 30 minutes?
- What happens if one tenant floods the queue?
- What happens if deployment happens while jobs are running?

إذا لم تكن لديك إجابات، فالنظام غير جاهز.

## 192. Multi-Tenant Fairness

إذا أرسل Tenant A عددًا كبيرًا من tasks وأرسل Tenant B عددًا قليلًا، فقد تهيمن A على workers إن لم توجد policy. قد تحتاج إلى per-tenant queues أو priority أو rate limits أو separate pools أو quota.

## 193. Rate Limiting Tasks

إذا كان External API يسمح بـ100 requests/min وكان لديك 20 workers، فقد ترسل 100 requests/sec وتكسر API. لدى Celery task rate-limit capabilities، لكن لا تعتمد عليها وحدها دون فهم workload وbroker وdownstream limits.

## 194. مهمة تعتمد على Redis Cache من الدرس السابق

تخيل `generate_recommendations(user_id)`: يحاول worker `cache.get()`؛ إذا كان هناك hit يعيد النتيجة، وإذا كان miss ينفذ heavy computation ثم يحفظ النتيجة في Redis. هنا بدأ دمج Redis وCelery وFastAPI.

## 195. Architecture تجمع الدرسين

```text
                 FastAPI
                    │
                 Request
                    │
                    ▼
                  Cache?
                 /      \
               HIT      MISS
                │          ↓
                │      Queue Task
                │          ↓
                │      RabbitMQ
                │          ↓
                │       Celery
                │          ↓
                │      Heavy Work
                │          ↓
                │        Redis
                │          │
                └──────────┴────────────►
```

هذه بداية backend حقيقي.

## 196. المشروع النهائي للدرس

**Production Report Processing Platform**:

```text
POST /reports
GET /reports/{report_id}
GET /tasks/{task_id}
POST /reports/{report_id}/retry
```

## 197. `POST /reports`

Request:

```json
{
  "type": "sales",
  "period": "2026-09"
}
```

FastAPI تقوم بـ:

1. Validate
2. Create DB row
3. Enqueue task
4. Return 202

## 198. Celery task

```python
@app.task(
    bind=True,
    autoretry_for=(TemporaryError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def generate_report(
    self,
    report_id: int,
):
    ...
```

## 199. Worker Flow

```text
Task starts
    ↓
load report
    ↓
mark PROCESSING
    ↓
load data
    ↓
generate report
    ↓
upload
    ↓
mark COMPLETED
    ↓
save output_url
```

## 200. Failure Flow

```text
External timeout
      ↓
retry
      ↓
backoff
      ↓
retry
      ↓
success
```

أو بعد استنفاد المحاولات:

```text
max retries
      ↓
FAILED
```

## 201. Idempotency Requirement

إذا نفذت `generate_report(123)` مرتين، فيجب ألا تنشئ نتيجتين تجاريتين متناقضتين. يمكن استخدام `report_id` كـbusiness identity.

## 202. Observability Requirement

أظهر `task_id` و`report_id` و`user_id` و`started_at` و`completed_at` و`duration` و`status` و`attempt` و`error`.

## 203. Load Test

أرسل 1,000 reports ثم قارن 1 worker و4 workers و8 workers من حيث queue wait وexecution time وthroughput وCPU وRAM وDB load.

## 204. Final Experiment

أرسل 100 tasks، مدة كل منها 5 ثوانٍ، وقارن:

- الحالة A: worker واحد، `concurrency=1`.
- الحالة B: worker واحد، `concurrency=4`.
- الحالة C: 3 workers، `concurrency=4`.

قارن النتائج لتفهم Concurrency مقابل Parallelism مقابل Worker scaling.

## 205. لكن لا تكتفِ بالنتيجة

اكتب: WHY did C outperform A? يجب أن تتضمن الإجابة execution slots أكثر، parallel work أكثر، shared queue، وindependent worker processes.

## 206. Exercise — Poison Task

أنشئ task تفشل دائمًا ثم أضف autoretry. راقب retry count وسلوك queue وworker. أضف `max_retries` واشرح لماذا لا تريد retry forever.

## 207. Exercise — Duplicate Execution

أنشئ task ذات `task_id = X` ثم اجعل worker يموت أثناء التنفيذ. راقب إعادة التنفيذ واكتب `DUPLICATE_EXECUTION.md`، وأجب: لماذا حدث التكرار؟ هل كان bug؟ وكيف نحمي business operation؟

## 208. Exercise — Slow Worker

شغّل task مدتها 60 ثانية ثم 100 tasks. راقب queue depth ثم زِد worker count. استنتج كم worker تحتاج، واربط الإجابة بطبيعة المهمة لا بالـCPU فقط.

## 209. Exercise — Multi-Queue Architecture

أنشئ queues باسم `reports` و`emails` و`ai`، وشغّل report-worker وemail-worker وai-worker. اختبر 1,000 report tasks مع 5 email tasks وأثبت أن email pipeline ما زالت تعمل.

## 210. Exercise — Scheduled Cleanup

استخدم Celery Beat لتشغيل `cleanup_reports` كل 10 minutes. تأكد أن Beat يطلق task بينما Worker ينفذها. Celery Beat مخصص لتوليد المهام المجدولة، ثم تقوم workers بتنفيذها.

## 211. Exercise — Chain

ابنِ workflow مستقلًا لكل خطوة:

```text
create_report
    ↓
generate_pdf
    ↓
upload_pdf
    ↓
notify_user
```

ثم اربطها بـchain.

## 212. Exercise — Group + Chord

لتقرير شهري، نفذ `fetch_sales` و`fetch_returns` و`fetch_customers` و`fetch_products` ثم `aggregate` باستخدام `group` و`chord`.

## 213. اختبار الفهم — المستوى الأول

- ما المشكلة التي تحلها task queue؟
- ما الفرق بين BackgroundTasks وCelery؟
- ما هو RabbitMQ؟
- ما هو Celery؟
- ما هو worker؟
- ما هو producer؟
- ما هو broker؟
- ما هو result backend؟
- لماذا نستخدم HTTP 202؟
- ما الفرق بين `delay()` و`apply_async()`؟

## 214. المستوى الثاني

- ما هي queue؟
- ما هو acknowledgement؟
- ما معنى `acks_late`؟
- لماذا يؤدي late ack إلى أهمية idempotency؟
- ما معنى retry؟
- ما هو exponential backoff؟
- ما هو jitter؟
- ما هو prefetch؟
- لماذا قد يكون `prefetch=1` مفيدًا للمهام الطويلة؟
- ما الفرق بين concurrency وworkers؟

## 215. المستوى الثالث

- لماذا لا نضع objects ضخمة داخل task message؟
- لماذا لا نمرر ORM objects؟
- لماذا لا يجب أن ينتظر FastAPI نتيجة task؟
- لماذا result backend ليس broker؟
- ما هو poison task؟
- لماذا retry لكل exception قد يكون خطأ؟
- ما الفرق بين transient وpermanent errors؟
- ما هو workload isolation؟
- لماذا نستخدم multiple queues؟
- ما هو queue backlog؟

## 216. المستوى الرابع

- ماذا يحدث لو مات worker بعد تنفيذ side effect وقبل الـack؟
- كيف تمنع duplicate payment؟
- لماذا لا تعني durable message وجود exactly-once business effect؟
- كيف تصمم task idempotent؟
- متى تستخدم chain؟
- متى تستخدم group؟
- متى تستخدم chord؟
- لماذا لا تستخدم `.get()` داخل worker على subtask؟
- كيف تتعامل مع queue growing indefinitely؟
- كيف تعمل horizontal worker scaling؟

## 217. المستوى الخامس — Senior

- صمّم processing platform لـ10 ملايين jobs/day.
- كيف تفصل CPU-heavy tasks عن I/O-heavy tasks؟
- كيف تمنع tenant واحدًا من استهلاك كل workers؟
- ماذا يحدث لو RabbitMQ unavailable أثناء enqueue؟
- ماذا يحدث لو RabbitMQ restarts؟
- ماذا يحدث لو Redis result backend unavailable؟
- كيف تمنع duplicate side effects؟
- كيف تعمل idempotency على payment task؟
- كيف تربط request ID بـtask ID؟
- كيف تبني autoscaling مبنيًا على queue depth؟

## 218. أكبر 20 قاعدة أريدها في دماغك

1. FastAPI handles HTTP.
2. RabbitMQ transports jobs.
3. Celery workers execute jobs.
4. Redis may store task results/state.
5. A queue absorbs bursts.
6. A queue does not create infinite capacity.
7. Worker count and API count scale independently.
8. Heavy tasks should not block HTTP requests.
9. Use 202 for accepted asynchronous work.
10. `delay()` is convenient; `apply_async()` gives more control.
11. Acknowledgement determines message-processing semantics.
12. Late ack improves redelivery behavior but increases duplicate-execution risk.
13. Late-acked tasks must be idempotent.
14. Retry transient errors, not permanent errors.
15. Backoff prevents retry storms.
16. Jitter prevents synchronized retries.
17. Prefetch matters for long-running tasks.
18. Separate workloads with queues.
19. Business state belongs in your domain/database when it must persist.
20. The hard part is not creating a Celery task. The hard part is correctness when failures happen.

## 219. الصورة الذهنية النهائية

لا أريدك أن ترى:

```python
@app.task
```

وتقول: «آه دي Celery». أريدك أن ترى:

```text
                HTTP REQUEST
                     │
                     ▼
                  FastAPI
                     │
               validate + persist
                     │
                     ▼
                  publish
                     │
                     ▼
                 RabbitMQ
                     │
                   Queue
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Worker 1   Worker 2   Worker 3
          │          │          │
          ▼          ▼          ▼
       Execute    Execute    Execute
          │          │          │
          └──────────┼──────────┘
                     ▼
               DB / Storage
                     │
                     ▼
                Result/State
```

ثم تضيف في ذهنك: `ACK` و`RETRY` و`BACKOFF` و`JITTER` و`PREFETCH` و`IDEMPOTENCY` و`ROUTING` و`CONCURRENCY` و`OBSERVABILITY` و`FAILURE HANDLING`.

## 220. الفرق بين مبتدئ وBackend Engineer

المبتدئ يقول: «هحط Celery عشان المهمة طويلة». أما Backend Engineer فيسأل:

- What is the workload?
- What is the arrival rate?
- What is the average task duration?
- What is the P95?
- Can the task run more than once?
- What happens if worker dies?
- What happens if RabbitMQ dies?
- Should this task retry? On which errors? How many retries?
- What queue should it use? What concurrency? What prefetch?
- What is the business state?
- How do I monitor queue depth?
- How do I scale workers?

وهنا يبدأ التفكير الحقيقي في الأنظمة الموزعة.

## 221. العلاقة بين درس Redis وهذا الدرس

في الدرس السابق تعلمت:

```text
Redis → Cache → Fast reads → TTL → Invalidation → Stampede
```

الآن:

```text
RabbitMQ → Queue → Workers → Acknowledgements → Retries → Scaling
```

وبعد قليل سنجمع FastAPI وPostgreSQL وRedis وRabbitMQ وCelery، ثم Microservices وEvents وKafka وDistributed Systems، ثم AI وRAG وEmbeddings وAsync ingestion وBackground processing.

## 222. وعندها يصبح RAG Production System مثلًا

```text
                    Client
                       │
                       ▼
                    FastAPI
                       │
                Upload Document
                       │
                       ▼
                  PostgreSQL
                       │
                       ▼
                   RabbitMQ
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
           Extract   Chunk    Metadata
              │        │
              └────┬───┘
                   ▼
              Embedding Worker
                   │
                   ▼
              Vector Store
                   │
                   ▼
                 Redis
                   │
                   ▼
                FastAPI
```

هذه ليست فكرة منفصلة؛ إنها نتيجة طبيعية لما تتعلمه الآن.

## 223. خلاصة الدرس

Celery ليس مجرد `@app.task`، وRabbitMQ ليس مجرد Queue. أنت تتعلم كيف تحول:

```text
Synchronous HTTP workflow
```

إلى:

```text
Asynchronous Distributed Workflow
```

بحيث:

- **FastAPI** تستقبل الطلب بسرعة.
- **RabbitMQ** تمثل طبقة النقل والـbuffering.
- **Celery** تدير تنفيذ العمل على workers.
- **Redis** يمكن أن يخزن النتائج والحالة المؤقتة.
- **PostgreSQL** تمثل business source of truth عندما يحتاج النظام ذلك.

ثم تبدأ الهندسة الحقيقية: Failure وRetry وConcurrency وIdempotency وScaling وObservability.

والقاعدة الأهم:

> لا تسأل: «كيف أشغل المهمة في الخلفية؟» اسأل: «كيف أجعل تنفيذ هذه المهمة موثوقًا عندما يحدث crash أو retry أو duplicate أو overload أو network failure؟»

عندما تبدأ التفكير بهذه الطريقة، تكون خرجت من مستوى استخدام Celery إلى مستوى هندسة أنظمة تعتمد على queues والworkers.

**مراجع رسمية اعتمدت عليها المادة في التفاصيل الحالية:** FastAPI BackgroundTasks، وCelery 5.6 documentation، وRabbitMQ 4.x work-queue/acknowledgement documentation.
