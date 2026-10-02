# هندسة التخزين المؤقت (Caching) باستخدام Redis في FastAPI

**المرحلة:** Redis & Caching

## 1. قبل Redis: ما هو الـCaching أصلًا؟
خلينا ننسى Redis لمدة دقائق. تخيل عندك API:

```http
GET /products/42
```

والتنفيذ الحقيقي للطلب:
```text
Client
  ↓
FastAPI
  ↓
Service
  ↓
PostgreSQL
  ↓
Service
  ↓
FastAPI
  ↓
Client
```
هذا طبيعي. لكن تخيل أن المنتج رقم 42 يتم طلبه بمعدل **100 requests/sec**، وكل request يعمل:

```text
FastAPI
   ↓
PostgreSQL
   ↓
SELECT * FROM products WHERE id = 42
```
مع أن النتيجة نفسها غالبًا لم تتغير.
إذن لدينا مشكلة: **لماذا أعيد حساب أو جلب نفس البيانات من المصدر البطيء آلاف المرات بينما أستطيع الاحتفاظ بنسخة سريعة منها؟**

وهنا يظهر الـCache. الفكرة:

```text
             ┌───────────────┐
             │   FastAPI     │
             └───────┬───────┘
                     │
                Cache lookup
                     │
             ┌───────▼───────┐
             │     Redis     │
             └───────┬───────┘
                     │
              HIT? ───┴─── NO
               │            │
              YES           ▼
               │       PostgreSQL
               │            │
               │            ▼
               │         Save to
               │          Redis
               │            │
               └────────────┘
```
إذن:
*   **Database** = Source of Truth (مصدر الحقيقة)
*   **Redis** = Fast temporary copy (نسخة مؤقتة سريعة)

وهذه الجملة من أهم الجمل في الدرس كله.

## 2. أهم فكرة: الـCache ليس Database ثانية
خطأ شائع جدًا: *"أنا عندي PostgreSQL وRedis، إذن البيانات موزعة بينهما."*
**لا.** في أغلب أنظمة caching، Redis ليس المصدر الرئيسي للحقيقة.
مثلًا في PostgreSQL:
`user 42 = Ahmed`
والـRedis:
`user:42 = Ahmed`

Redis هنا نسخة مؤقتة.
لو Redis وقع: `Redis ❌ | PostgreSQL ✅` المفروض النظام يستطيع إعادة بناء الـcache.
أما لو: `PostgreSQL ❌ | Redis ✅` فلا ينبغي أن تعتبر Redis بديلًا دائمًا لقاعدة البيانات إلا إذا أنت أصلًا صممت النظام بهذه الطريقة.

## 3. لماذا نحتاج Caching؟
Caching يحاول حل مجموعة من المشاكل:

### 3.1 تقليل Database Load
بدل `1000 requests → 1000 database queries`
يمكن أن تصبح `1000 requests → 1 database query → 999 cache hits` تقريبًا.

### 3.2 تقليل Latency
الطلب الذي يحتاج إلى `API → DB` عادة يحتوي على network hop + query + database processing.
بينما `API → Redis` قد يكون أبسط وأسرع بكثير، خصوصًا عندما تكون البيانات صغيرة ومكررة الاستخدام. Redis يوفّر أنواع بيانات أصلية مثل Strings وHashes وLists وSets وSorted Sets، وتُستخدم الـStrings كثيرًا لتخزين بيانات الـcache.

### 3.3 حماية الـDatabase من الضغط
تخيل أن Product catalog يحصل على مليون قراءة خلال دقائق. لو كل قراءة ذهبت إلى PostgreSQL:
```text
PostgreSQL
████████████████████████████
```
لكن لو معظمها cache hits:
```text
Redis
████████████████████████████

PostgreSQL
██
```
فالـdatabase تحصل على workload أقل.

## 4. ما الذي يجب أن نُخزنه في Cache؟
هنا تبدأ الهندسة الحقيقية. ليس معنى وجود Redis أنك يجب أن تعمل cache لكل شيء. اسأل:

**هل البيانات تُقرأ كثيرًا؟**
مثل: (products, categories, popular posts, configuration, permissions, public profile) -> هذا جيد.

**هل البيانات تتغير قليلًا؟**
مثال: (country list, categories, product details) -> ممتاز.

**هل إعادة حسابها مكلفة؟**
مثل: (expensive SQL query, aggregation, report summary, expensive API call, LLM response) -> غالبًا ممتاز.

## 5. متى لا يكون Caching مناسبًا؟
مثال: `GET /account/balance`
لو البيانات يجب أن تكون شديدة الحداثة، قد يكون cache غير مناسب أو يحتاج تصميمًا دقيقًا.
أيضًا: `POST /payment`
هذا ليس مجرد شيء تريد تخزينه في cache. بل العكس، الـPayment غالبًا يحتاج (correctness, consistency, idempotency, transaction safety) وليس مجرد `GET → SET`.

## 6. المعادلة الذهنية للـCache
قبل عمل cache لأي endpoint، تذكر هذه المعادلة:
**Cache Value = Read Frequency × Read Cost × Acceptable Staleness**

كلما كان `Read Frequency ↑` و `Read Cost ↑` و `Acceptable Staleness ↑`، يزداد احتمال أن يكون caching مناسبًا. لكن هذا ليس قانونًا رياضيًا حرفيًا، هو Mental Model لاتخاذ القرار.

## 7. Cache Hit و Cache Miss
هذه أهم مصطلحين:

**Cache Hit:** عندما يبحث التطبيق عن البيانات في Redis ويجدها:
```text
GET product:42 → value exists (CACHE HIT)
```

**Cache Miss:** عندما لا يجدها:
```text
GET product:42 → nil (CACHE MISS)
```
وفي هذه الحالة نذهب إلى database:
```text
Redis
  ↓
MISS
  ↓
PostgreSQL
  ↓
Data
  ↓
Redis SET
  ↓
Response
```

## 8. أهم Pattern: Cache-Aside
الـpattern الأساسي الذي سنستخدمه في FastAPI هو **Cache-Aside** ويُسمى أحيانًا **Lazy Loading Cache**.
Redis توثّق هذا النمط باعتباره: اقرأ من Redis أولًا، وإذا حدث miss فاقرأ من المصدر الأساسي، ثم خزّن النتيجة مع TTL؛ وعند الكتابة يمكن إبطال المفتاح لتقليل فترة الـstaleness.

التنفيذ:
```python
value = await redis.get(key)

if value is not None:
    return value

value = await database.get(...)
await redis.set(key, value, ex=60)

return value
```
هذه الخمس سطور تقريبًا هي قلب الـcache-aside.

## 9. افهم Cache-Aside كـState Machine
اعتبر أن عندك Cache State قد تكون: `ABSENT`, `VALID`, `EXPIRED`, `INVALIDATED`.

عند القراءة:
```text
Request
  ↓
Cache?
  ├── HIT → Return
  │
  └── MISS
         ↓
      Database
         ↓
       Cache
         ↓
       Return
```
وعند التحديث:
```text
Write DB
   ↓
Invalidate Cache
```
غالبًا:
```python
await db.update_user(user_id, data)
await redis.delete(f"user:{user_id}")
```
وهذا بسيط جدًا ظاهريًا، لكن وراءه مشاكل عميقة جدًا.

## 10. Redis كـKey-Value Store
أبسط شكل: `KEY → VALUE`
مثال:
`product:42 → {"id":42,"name":"Keyboard","price":100}`
أمر Redis المفاهيمي:
```redis
SET product:42 "{...}"
GET product:42
```
Redis Strings مناسبة جدًا لهذا الاستخدام، وSET يدعم أيضًا خيارات expiration مثل EX وPX.

## 11. لماذا الـKey Design مهم جدًا؟
لأن Redis لا يعرف أن `42` يعني `product id`. أنت من يحدد ذلك.
إذن `42` هو Key سيئ.
الأفضل: `product:42` أو `cache:product:42` أو `api:v1:product:42`.

## 12. Naming Convention
استخدم هيكلًا واضحًا.
مثال: `user:42`, `product:100`, `order:500`.
لكن في مشروع كبير: `cache:v1:user:42`.
**لماذا v1؟**
لأنك قد تغير شكل البيانات. اليوم:
```json
{
  "id": 42,
  "name": "Ahmed"
}
```
غدًا:
```json
{
  "id": 42,
  "full_name": "Ahmed",
  "email": "..."
}
```
يمكنك تغيير `user:v1:42` إلى `user:v2:42` وبالتالي تتجنب collision مع schema قديم.

## 13. الـCache Key يجب أن يمثل كل Inputs المهمة
مثال endpoint: `GET /products?page=2&limit=20&category=keyboard`
لا يصح أن يكون key فقط `products` لأن `page=1` و `page=2` سيحصلان على نفس القيمة.
يجب أن يحتوي المفتاح على parameters المؤثرة:
`products:page:2:limit:20:category:keyboard`
أو الأفضل عادة توليد key canonical. مثال:
```python
key = (
    f"products:"
    f"page={page}:"
    f"limit={limit}:"
    f"category={category or 'all'}"
)
```

## 14. Serialization
Redis لا يفهم Python object تلقائيًا بالشكل الذي تتخيله. لا يمكنك التفكير في الموضوع كأنك ستضع object عاديًا داخل Redis وانتهى الأمر.
غالبًا سنحوّل البيانات إلى **JSON**:
```python
# عند الكتابة
json.dumps(...)

# وعند القراءة
json.loads(...)
```

## 15. لماذا JSON؟
لأنه: Human-readable, Language-independent, Easy to inspect, Easy to move between services.
لكن له تكلفة:
`Python object ↓ serialization ↓ JSON ↓ Redis ↓ JSON ↓ deserialization ↓ Python object`
إذن serialization نفسها لها تكلفة. لا تفترض أن Redis دائمًا أسرع لمجرد أن Redis موجود. الـcache له overhead: network, serialization, deserialization, memory, connection, key generation.
لكن عندما تكون تكلفة الـsource أعلى بوضوح، يكون المكسب كبيرًا.

## 16. تثبيت Redis Client في Python
سنستخدم:
```bash
python -m pip install redis
```
والـPython client الرسمي الحالي هو `redis-py`، ويدعم Asyncio عبر:
```python
import redis.asyncio as redis
```
كما يدعم إنشاء الاتصال من URL مثل `redis://localhost:6379` وإغلاق العميل async بشكل صريح عبر `aclose()`.

## 17. أول اتصال بـRedis
```python
import redis.asyncio as redis

client = redis.Redis.from_url(
    "redis://localhost:6379",
    decode_responses=True,
)

await client.set("name", "Ahmed")
value = await client.get("name")
print(value) # Ahmed
```

## 18. لماذا decode_responses=True؟
بدونه قد تتعامل مع `b"Ahmed"` بدل `"Ahmed"`. وهذا مهم خصوصًا في APIs التي تتعامل مع JSON.

## 19. FastAPI لا يجب أن ينشئ Redis Connection مع كل Request
هذا خطأ تصميم شائع:
```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    redis_client = redis.Redis(...) # ❌ خطأ
```
لأنك قد تنشئ client/resource بشكل متكرر. الأفضل أن تنشئ resource تشاركه الـrequests. FastAPI يوفر `lifespan` لإعداد موارد التطبيق قبل استقبال requests وتنظيفها عند shutdown.

## 20. تصميم Redis داخل FastAPI
```text
FastAPI startup
      ↓
Create Redis client/pool
      ↓
Application runs
      ↓
Requests use Redis
      ↓
Shutdown
      ↓
Close Redis
```

## 21. الهيكل الأول
```text
app/
├── main.py
├── cache.py
├── config.py
└── routes/
    └── users.py
```

## 22. config.py
```python
import os

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)
```

## 23. cache.py
```python
import redis.asyncio as redis

class RedisCache:
    def __init__(self, url: str):
        self.client = redis.Redis.from_url(
            url,
            decode_responses=True,
        )

    async def close(self) -> None:
        await self.client.aclose()
```

## 24. main.py
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.cache import RedisCache
from app.config import REDIS_URL

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = RedisCache(REDIS_URL)
    yield
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)
```
لاحظ الفكرة: `app.state.redis` أصبح موردًا مشتركًا للـapplication.

## 25. لكن لا نريد Redis Logic داخل Route
لا تكتب كل منطق Redis والـ JSON Parsing داخل الـ Route وتكرره 20 مرة. هذا يجعل الـroutes متضخمة.

## 26. Architecture
```text
                FastAPI Route
                      │
                      ▼
                User Service
                  /       \
                 /         \
                ▼           ▼
             Redis       Repository
                           │
                           ▼
                       PostgreSQL
```
وهكذا يصبح الـcache concern منظمًا.

## 27. أول Cache Helper
```python
import json
from typing import Any

class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_json(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        await self.redis.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)
```

## 28. تنفيذ Cache-Aside كامل
```python
async def get_user(user_id: int):
    key = f"user:{user_id}"
    cached = await cache.get_json(key)

    if cached is not None:
        return cached

    user = await user_repository.get_by_id(user_id)
    if user is None:
        return None

    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }

    await cache.set_json(key, data, ttl=60)
    return data
```

## 29. افهم الطلب الأول بالتفصيل
أول request: `GET /users/42`
Redis: `GET user:42` → `nil` (MISS)
PostgreSQL يعيد البيانات، ثم يتم عمل `SET user:42 JSON EX 60` ثم response.

## 30. الطلب الثاني
نفس الطلب `GET /users/42`
Redis: `GET user:42` → النتيجة موجودة (HIT)
فنرجع البيانات مباشرة. لا يوجد query إلى PostgreSQL.

## 31. لماذا نستخدم TTL؟
الـTTL (Time To Live) يعني: كم من الوقت يجوز أن تعيش القيمة في الـcache؟
```python
await redis.set("user:42", value, ex=60)
```
بعد 60 ثانية المفتاح ينتهي ويُحذف تلقائياً.

## 32. لماذا TTL مهم جدًا؟
لأن بدون TTL قد يحدث:
Database: `price = 100` | Redis: `price = 100`
ثم تغير السعر في الداتابيز إلى `120`، لكن Redis ما زال `100`. إذا لم يحدث invalidation أو expiration، يمكن أن يستمر الـstale data للأبد.

## 33. TTL ليس حلًا سحريًا
`TTL = 60s` لا يعني: "البيانات صحيحة لمدة 60 ثانية."
بل يعني: **"نحن نقبل احتمال تقديم نسخة قديمة ضمن هذا التصميم لمدة تصل تقريبًا إلى هذا الحد."**
هذا فرق فلسفي مهم جدًا.

## 34. Stale Data
لدينا: `Database = 120`, `Cache = 100`. الـcache هنا STALE (قديم).
السؤال: هل أستطيع قبولها؟ يعتمد على الـ domain.
(exchange rate, payment status) -> تحتاج freshness أعلى بكثير.
(blog post, product description) -> قد تتحمل stale data لفترة.

## 35. اختيار TTL
لا يوجد رقم سحري. لا تقل دائمًا 300 seconds. بل **TTL = Business Requirement**.
مثال: countries → hours, categories → minutes, homepage feed → seconds.

## 36. TTL قصير جدًا
إذا `TTL = 1 second` فقد يحدث MISS → DB → SET بشكل متكرر ومزعج، وبالتالي: `Cache Hit Rate ↓` و `Database Load ↑`.

## 37. TTL طويل جدًا
مثال `TTL = 24 hours` قد يعطي High hit rate لكن `Staleness ↑`. إذن هناك trade-off.

## 38. Cache Hit Ratio
من أهم metrics:
`Cache Hit Ratio = Cache Hits / (Cache Hits + Cache Misses)`
مثال: Hits = 9000, Misses = 1000. إذن 90% hit ratio.
لكن لا تنخدع بهذه النسبة وحدها إذا كانت serialization مكلفة جداً.

## 39. Cache Miss Ratio
ببساطة: `Miss Ratio = 1 - Hit Ratio` (في المثال: 10%).

## 40. أهم metric أخرى: Latency
راقب: cache hit latency, cache miss latency, database latency, serialization latency.

## 41. أهم درس معماري: Cache Invalidation
لماذا هو صعب؟ لأنك عندما تعدل المصدر الحقيقي (DB)، يجب أن تعرف ما الذي أصبح قديمًا في (Redis).

## 42. السيناريو الخطير
DB = Ahmed | Redis = Ahmed
`PUT /users/42`
يحدث: DB = Mohamed (ولكن نسيت تحديث Redis).
ثم `GET /users/42` يعود بـ Ahmed. هذه ليست مشكلة أداء، هذه **Correctness Problem**.

## 43. أبسط Invalidation Strategy
بعد نجاح write:
```python
await user_repository.update(...)
await cache.delete(f"user:{user_id}")
```
الطلب القادم سيجد MISS ويجلب البيانات الجديدة من الـ DB. طريقة ممتازة كبداية.

## 44. لماذا Delete بعد Database Update؟
نريد: `1. DB update → 2. Cache invalidation`
وليس العكس، لأن الترتيب المعكوس يفتح نافذة race condition.

## 45. Race Condition مهمة جدًا
لو Request A (WRITE) عمل DELETE cache، ثم تأخر في DB UPDATE.
وفي نفس اللحظة Request B (READ) عمل GET cache فجده miss، وقرأ الـ DB القديمة، وخزنها في Redis كقيمة جديدة.
ثم A ينتهي ويُحدّث الـ DB للقيمة الجديدة.
الآن: `DB = new` و `Redis = old`. هذه من أشهر مشاكل الـ cache invalidation.

## 46. إذن لماذا الأمر ليس بهذه البساطة؟
لأن DB و Redis نظامان منفصلان. لا يوجد بشكل تلقائي transaction مشتركة بينهما في أبسط Cache-Aside. الـcache consistency يجب تصميمها.

## 47. Write-Through
```text
Application → Cache → Database
```
الفكرة أن الكتابة تمر عبر الـcache. الميزة: cache remains warm، لكن التعقيد أكبر.

## 48. Write-Behind / Write-Back
```text
Application → Cache → Later → Database
```
هذا أخطر من ناحية consistency، لن نستخدمه كـ default.

## 49. Cache-Aside هو Default ممتاز للتعلم
لأن Read: `Cache → DB → Cache`
و Write: `DB → Invalidate Cache`
واضح ومفهوم، ويمكن تطويره لاحقًا.

## 50. Cache Stampede
تخيل: popular product والـTTL انتهى.
في نفس اللحظة: 10,000 requests كلهم يفعلون `GET product:42`.
الكل يجد MISS، والكل يذهب للـ DB. ينتهي بك الأمر بـ 10,000 DB queries في نفس الثانية.
هذا يُسمى **Cache Stampede** (أو Thundering Herd).

## 51. لماذا الـCache هنا زاد المشكلة؟
لأننا اعتمدنا عليه لمنع الحمل، لكن عند expiration حدث `All traffic → Database` في أسوأ لحظة ممكنة.

## 52. الحل الأول: Lock
الفكرة: أول Request يحصل على Lock، يذهب للـ DB ويملأ الـ Cache. باقي الـ Requests تنتظر حتى يمتلئ الكاش.
```text
GET lock:product:42
```

## 53. Redis NX
Redis SET يدعم شرط `NX` (Set only if key does not already exist).
```python
acquired = await redis.set("lock:product:42", "1", ex=5, nx=True)
```

## 54. لماذا نحتاج TTL للـLock؟
لأن هذا السيناريو كارثي: request gets lock → process crashes → lock remains forever. يجب أن ينتهي القفل، مثلاً `TTL = 5 seconds`.

## 55. Lock ليس مجرد Boolean
في production استخدم unique token لتضمن أن من أنشأ الـ lock هو فقط من يمسحه.
```python
token = uuid.uuid4().hex
```

## 56. Cache Stampede Solution أخرى (TTL Jitter)
بدل انتظار expiration بالضبط (TTL = 60)، يمكن إضافة رقم عشوائي:
`ttl = 60 + random(0, 20)`
حتى لا تنتهي آلاف المفاتيح في نفس اللحظة. يسمى هذا **TTL Jitter**.

## 57. Early Refresh
إذا كان `TTL < 10s` يمكننا تحديث القيمة قبل الـ expiration الحقيقي عبر worker واحد بالخلفية بدلاً من انتظار الانتهاء وذهاب الجميع للـ DB.

## 58. Stale-While-Revalidate
تحتفظ بقيمة قديمة لفترة قصيرة وتعطي الـ user الـ stale data المقبولة، بينما في الخلفية يتم تحديثها.

## 59. Cache Avalanche
1,000,000 مفتاح تم إدخالهم بنفس الـ TTL (300s). ينتهون تقريباً معاً وتنهار الداتابيز بسبب الحمل. الحل: TTL jitter و warming.

## 60. Cache Penetration
عميل يطلب منتج غير موجود `/product/999999999`.
Redis يعطي MISS، و DB تعطي NOT FOUND. يتكرر الطلب ويهلك الداتابيز في البحث عن شيء غير موجود.

## 61. Negative Caching
يمكن تخزين `product:999999999 = NOT_FOUND` لفترة قصيرة (TTL = 10 sec) لتقليل الضغط.

## 62. Hot Keys
مفتاح واحد يحصل على معدل طلبات ضخم جداً. حتى Redis قد يصبح نقطة ضغط. الحلول تشمل local caching, request coalescing.

## 63. Redis ليس سحرًا
عندما تستخدم `FastAPI → Redis` أنت أضفت network dependency. يجب أن تقرر: هل الـ Cache إجباري أم اختياري (Optional) كتحسين للأداء فقط؟

## 64. Cache Failure Policy
لا تكتب:
```python
try:
    cached = await redis.get(key)
except:
    crash entire API # ❌ خطأ
```
يجب أن تتخطى الخطأ (Bypass Cache) وتجلب من الـ DB وهذا يسمى **Graceful Degradation**.

## 65. لكن انتبه
إذا كان Redis يستخدم للـ rate limiting أو sessions أو queues فليس كل فشل يمكن تجاوزه. استخدام Redis ككاش يختلف جذرياً عن كونه Data Store حرج.

## 66. Cache Security
لا تخزن أسرارًا (Passwords, access tokens, raw payment) في الكاش. وتأكد من وضعه في Private Subnet وليس مكشوفاً للإنترنت.

## 67. لا تستخدم User ID وحده عندما تكون البيانات Personalized
لو عملت الكاش باسم `dashboard` قد تعطي User A بيانات User B. يجب أن يمثل المفتاح الـ Context: `dashboard:user:42`.

## 68. Vary by Context
إذا الـ endpoint يتأثر بـ (user, language, currency, role)، يجب أن تكون جزءاً من المفتاح.

## 69. Multi-Tenant Systems
في تطبيقات الـ SaaS: استخدم `tenant:A:customer:42` بدلاً من `customer:42` لمنع تداخل البيانات بين الشركات.

## 70. Serialization مع Pydantic
يمكن تخزين representation الموديل:
```python
await redis.set(key, user.model_dump_json(), ex=60)
# وعند القراءة
UserResponse.model_validate_json(cached)
```

## 71. ماذا عن Schema Versioning؟
لو أضفت حقل `role` جديد للموديل، الكاش القديم سيسبب مشاكل. الحل وضع نسخة للمفتاح: `user:v1:42` و `user:v2:42`.

## 72. Redis Data Types
Redis يوفر أنواعًا مثل (Strings, Hashes, Lists, Sets, Streams, JSON).

## 73. Strings
أفضل بداية للـAPI response caching `user:42 → {"id":42,"name":"Ahmed"}`.

## 74. Hashes
مناسب لقراءة/تحديث حقول معينة باستمرار داخل الأوبجيكت دون استدعائه بالكامل.

## 77. أهم قاعدة
لا تختار Redis data type لأن “شكله أجمل.” بل لأنه يخدم الـ Access Pattern للنظام.

## 79. Connection Pool
لا تبني اتصال TCP جديد مع كل ريكويست. الـ Python client يستخدم Connection Pools لإدارة الاتصالات عبر الـ Lifespan.

## 81. Dependency Injection
```python
def get_redis(request: Request):
    return request.app.state.redis.client
```

## 82. الأفضل: Cache Service
افصل المنطق في خدمة مستقلة:
```python
class CacheService:
    def __init__(self, redis):
        self.redis = redis

    async def get(self, key):
        return await self.redis.get(key)
    
    # ...
```

## 84. Cache-Aside في شكل Architecture
```text
                     GET /users/42
                           │
                           ▼
                       FastAPI
                           │
                           ▼
                      UserService
                       /       \
                      /         \
                     ▼           ▼
                 CacheService   Repository
                     │             │
                     ▼             ▼
                  Redis         PostgreSQL
```

## 85. Cache Miss ليس Error
لا تفعل `raise Exception("Cache miss")`، هذا مسار متوقع (Expected Control Flow).

## 86. Cache Error ≠ Cache Miss
- `key does not exist` = MISS
- `connection timeout` = INFRASTRUCTURE FAILURE

## 87. Observability
لا يكفي أن تقول "Redis يعمل". راقب: `hits, misses, errors, latency`.

## 88. Logging
```python
logger.info("cache_hit", extra={"key": key})
```
(واحذر من تسجيل الـ Secrets).

## 90. لماذا Metrics أهم من الإحساس؟
لأن "Redis سريع" ليس measurement. بينما `P95 cache GET = 3ms` و `Hit Ratio = 93%` هي معلومات دقيقة.

## 92. Redis Memory
Redis هو In-Memory Data Store. راقب حجم الـ Memory وسياسة الـ Eviction عند الامتلاء.

## 95. Cache Warmup
تحميل بيانات هامة مسبقاً للكاش عند الـ Startup لتجنب الـ Misses في البداية.

## 98. Prefixes
اختر Naming Convention موحد: `{domain}:{entity}:{version}:{identifier}` (مثال: `catalog:product:v1:42`).

## 99. Cache Query Results
تخزين نتائج البحث `products:category:10:page:1`. لكن الـ Invalidation هنا أصعب بكثير.

## 100. Object Cache مقابل Response Cache
`Object Cache` يخزن العنصر (User)، بينما `Response Cache` يخزن استجابة الـ API كاملة (بـ Headers).

## 103. لا تعمل Cache لكل Endpoint تلقائيًا
"أي GET = Redis" هي عادة مبتدئ. اسأل نفسك هل النتيجة تتكرر وهل يمكن تقديمها كـ Stale Data؟

## 105. Multi-Level Caching
`Browser → CDN → Nginx → FastAPI → Redis → PostgreSQL`

## 109. Caching للـExpensive Computation
يمكن حفظ نتيجة تقرير يأخذ ثانيتين ليتم توليده `report:user:42:period:2026-10`.

## 111. Caching للـLLM Responses
يمكن استخدام تجزئة الـ Prompt `sha256(prompt)` כמفتاح لحفظ استجابات الذكاء الاصطناعي لتقليل التكلفة.

## 114. Single-Flight Mental Model
بدلاً من 10 طلبات ثقيلة متوازية، نفذ طلباً واحداً وشارك نتيجته مع الـ 9 الباقين. مفهوم محوري في الـ Distributed Systems.

## 115. Cache + Database Transactions
يجب ربط مسح الكاش بنقطة نجاح الـ Commit في قاعدة البيانات، وإلا ستقوم بمسحه قبل أن تكتمل الـ Transaction بنجاح.

## 116. Event-Based Cache Invalidation
نشر حدث `UserUpdated` لخدمة أخرى تقوم هي بمسح الكاش عبر Kafka أو RabbitMQ.

## 118. Eventual Consistency
النافذة الزمنية البسيطة التي يكون فيها الـ DB محدثاً بينما الكاش يحمل بيانات قديمة للحظات.

## 119. Cache Correctness Questions
أسئلة قبل الـ Production: "من أين الحقيقة؟ متى تنتهي الصلاحية؟ ماذا لو سقط Redis؟"

## 120. Redis + FastAPI Production Pattern
استخدم هيكل مجلدات نظيف يفصل `infrastructure`, `cache`, `users/router`, و `tests`.

## 121. لماذا keys.py؟
لا تكتب النصوص موزعة، بل استخدم دالة لتوليدها `def user_cache_key(id): ...` لدعم الـ Refactoring بسهولة.

## 126. Dependency Direction
اجعل الـ Application يعتمد على Interface (Port) لتسهيل الـ Mocking والاختبارات.

## 127. Testing Cache Logic
اختبر 4 حالات رئيسية: Hit, Miss, DB Not Found, Redis Failure.

## 131. أهم Error Handling Trap
لا تستخدم `except Exception` وتخفي أخطاء السيرفر الحقيقية. اصطد `except RedisError` فقط لعمل Fallback.

## 133. Timeout
احذر من الـ Retry Storm. لا تضع إعادة محاولة لانهائية تجعل السيرفر ينهار بسبب الضغط.

## 135. Circuit Breaker Mental Model
إذا كثرت أخطاء Redis، قم بتجاوزه مؤقتاً (Open Circuit) حتى يتعافى.

## 137. Cache and Rate Limiting
استخدم الكاش كـ Counters للتحكم بمعدل الطلبات باستخدام `INCR` و `EXPIRE`.

## 141. Atomicity
عمليات Redis مثل `INCR` هي Atomic بطبيعتها، وتمنع الـ Race Conditions في العدادات.

## 143. Redis Pipeline
تجميع عدة أوامر لتقليل الـ Network Round Trips.

## 146. Cache Read Path
احفظ هذا التدفق: `Build Key → Try Cache → (Hit ? Return : Load Source → Store → Return)`

## 147. Cache Write Path
`Validate → DB Transaction → Success? → Invalidate Cache → Response`

## 151. Example كامل (User Service)
نموذج تطبيقي عملي يدمج الـ Repository و الـ Cache Service مع عمليات القراءة والتحديث والمسح.

## 154. Security Boundary
لا تترك Redis مكشوفاً (Exposed) للإنترنت أبداً.

## 156. Environment Variables
استخدم `REDIS_URL = os.environ["REDIS_URL"]` ولا تضع كلمات المرور في الكود أبداً.

## 158. Exercises التدريب العملي (1 to 15)
قم بتطبيق هذه التمارين البرمجية (الـ Basics، الـ TTL، الـ Cache-Aside، الـ Stampede، والـ Lock) خطوة بخطوة لبناء العضلات البرمجية.

## 173. Production Design Checklist
مر على هذه القائمة (Source of Truth, Keys, TTL, Security, Metrics) قبل إطلاق أي نظام Caching.

## 174. الأخطاء التي أريدك ألا ترتكبها
- Redis ليس Database أساسية.
- لا تعمل Cache لكل GET.
- الفشل ليس Miss.
- لا تمسح كاش في أي مكان عشوائي دون فهم.

## 178. سؤال Senior مهم جدًا: "Why Redis?"
الإجابة الهندسية: *"لدينا نظام يحتاج لقراءات متكررة، و PostgreSQL هو مصدر الحقيقة، بينما Redis يحمل نسخ مؤقتة بـ TTL ومسح ذكي عند التحديث لتخفيف الضغط."*

## 183. Cache Key Design Exercise
صمم جدولاً يحتوي على الـ Endpoint، الـ Key، الـ TTL، وشرط الـ Invalidation. إذا لم تستطع، فأنت لم تصمم الكاش بعد.

## 184. مشروع الدرس النهائي: Production-Style FastAPI Caching Layer
قم ببناء نظام متكامل يحتوي على خدمات المستخدين والمنتجات مع تطبيق سياسات القراءة، الكتابة، الـ Lock، ومراقبة الـ Metrics.

## 194. أهم 15 قاعدة أريدها في دماغك
(مراجعة القواعد الذهبية لمهندس الأنظمة الموزعة: الـ Cache هو تحسين للأداء، الـ DB هي الأساس، الـ Cache Hit نجاح متوقع، والـ TTL ليس بديلاً للاتساق).

## 195. الصورة الذهنية النهائية للمسارات
فهم دقيق لكيفية مرور الطلبات في حالات (النجاح، الكتابة، الفشل، والضغط العالي Concurrency).

## 197. الخلاصة
الهندسة الحقيقية هي أن تعرف كيف تدير:
**DATA + TIME + LOAD + CONSISTENCY + CONCURRENCY + FAILURE**

Redis ليس الهدف، الهدف أن تعرف كيف تجعل نظام FastAPI أسرع وأكثر تحملًا للـ Load، بدون أن تفسد الـ Correctness.