from __future__ import annotations
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set before resetting and seeding.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TRACK_DATA = {
    "name": "هندسة الباك إند والذكاء الاصطناعي",
    "slug": "backend-ai-engineering",
    "description": "مسار عملي متكامل لبناء خدمات باك إند موثوقة باستخدام Python وFastAPI وPostgreSQL، ودمج نماذج اللغة والبحث المتجهي وأنظمة RAG، ثم تجهيز التطبيق للنشر والتشغيل الإنتاجي.",
    "ordering": 1,
    "is_premium": True,
    "price": 5600.00,
    "currency": "EGP",
    "is_active": True,
}

YOUTUBE_EMBED_PATTERN = re.compile(
    r"https://www\.youtube\.com/embed/[A-Za-z0-9_-]{11}"
)

MODULES_DATA = [
    {
        "title": "Module 1: أساسيات الباك إند وبايثون المتقدمة",
        "description": "يبني هذا المسار أساساً عملياً في Python غير المتزامنة، وتصميم واجهات FastAPI، والتحقق من البيانات باستخدام Pydantic V2.",
        "ordering": 1,
        "lessons": [
            {
                "title": "البرمجة غير المتزامنة Async/Await في بايثون",
                "description": "تعرّف على event loop و coroutines وكيفية استخدام await لتنفيذ عمليات الشبكة و I/O بكفاءة.",
                "content": """
### 1. المقدمة والمفاهيم الأساسية: Sync vs Async وما وراء الكواليس (Under the Hood)

عند بناء أنظمة خلفية (Backend Services) حديثة باستخدام أطر عمل مثل **FastAPI** أو خوادم **ASGI** مثل Uvicorn، تصبح إدارة الموارد والتزامن (Concurrency) نقطة الفصل بين التطبيقات التي تتحمل ملايين الطلبات التزامنية وتلك التي تعاني من التجمّد والإبطاء.

**لماذا Async؟ (تجاوز عنق الزجاجة للـ GIL):**
في بايثون، يمنع الـ Global Interpreter Lock (GIL) تنفيذ أكثر من Thread واحد في نفس اللحظة. البرمجة غير المتزامنة (AsyncIO) لا تعتمد على نظام الـ OS Threads الثقيل الذي يستهلك الذاكرة (Memory Overhead)، بل تستخدم "خيطاً واحداً" (Single Thread) يدير آلاف المهام بذكاء عبر تبديل السياق (Context Switching) فقط عند فترات الانتظار.

```text
Synchronous Execution (Blocking):
[Request 1: Waiting I/O...] -> [Request 2: Waiting I/O...] -> [Request 3: Waiting I/O...]
Total Time = T1 + T2 + T3

Asynchronous Execution (Non-Blocking Event Loop):
[Request 1: Start I/O ──┐
[Request 2: Start I/O ──┼──> Event Loop switches during wait time ──> Completion]
[Request 3: Start I/O ──┘
Total Time ≈ Max(T1, T2, T3)
```

#### الفرق المعماري بين عمليات I/O-Bound و CPU-Bound:

| نوع العمليات | القيد الأساسي (Bottleneck) | الحل الأنسب في بايثون | أمثلة معمارية |
| --- | --- | --- | --- |
| **I/O-Bound** | الانتظار لرد السيرفرات، قواعد البيانات، أو أقراص التخزين. | **`asyncio` (Async/Await)** | الاستعلام من PostgreSQL، استدعاء REST APIs خارجية، قراءة ملفات من S3. |
| **CPU-Bound** | استهلاك قدرات المعالج في الحسابات المعقدة. | **`multiprocessing`** | معالجة الصور، التشفير المعقد، معالجة مصفوفات الذكاء الاصطناعي (NumPy). |

### 2. المحرك الداخلي: Event Loop و Coroutines

تعتمد البرمجة غير المتزامنة في بايثون على مكونين أساسيين:

1. **الـ Coroutine:** هي دالة تُعرّف بـ `async def`. عند استدعائها، لا تُنفّذ شفرتها فوراً، بل تُرجع كائن Coroutine يُمكن إيقافه مؤقتاً واستئنافه بكفاءة عالية جداً في الذاكرة مقارنة بالـ Threads.
2. **حلقة الأحداث (Event Loop):** المدير المركزي (المايسترو) الذي يدير جميع المهام (Tasks). يقوم بتشغيل الـ Coroutine، وعندما يصل إلى أمر `await` ينتظر عملية خارجية، يحوّل الـ Event Loop التحكم فوراً (في أجزاء من الملي ثانية) لمهمة أخرى جاهزة.

**دور الكلمة المفتاحية `await`:**

تُستخدم `await` فقط داخل الدوال المعرفة بـ `async def`. وتُخبر الـ Event Loop: *"سأنفذ هذه العملية المنتظِرة الآن، يمكنك استغلال موارد المعالج لخدمة مستخدمين آخرين حتى يأتيني الرد"*.

### 3. التطبيق العملي والمقارنة البرمجية (Sync vs Async)

في هذا المثال، سنحاكي جلب بيانات من 3 مصادر خارجية مختلفة (API, Database, Cache)، تستغرق كل منها ثانية واحدة.

#### الكود المتزامن التقليدي (Blocking - يهدر 3 ثوانٍ):

```python
import time

def fetch_user_data():
    time.sleep(1)  # محاكاة طلب شبكة متزامن (Blocking)
    return {"user_id": 101}

def fetch_orders_data():
    time.sleep(1)
    return [{"order_id": 5001}]

def fetch_analytics_data():
    time.sleep(1)
    return {"status": "active"}

def main_sync():
    start_time = time.perf_counter()

    user = fetch_user_data()
    orders = fetch_orders_data()
    analytics = fetch_analytics_data()

    elapsed = time.perf_counter() - start_time
    print(f"Sync Total Execution Time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main_sync()
```

#### الكود غير المتزامن الاحترافي (Non-Blocking - ينجز في ثانية واحدة فقط):

```python
import asyncio
import time

async def fetch_user_data():
    await asyncio.sleep(1)  # محاكاة طلب شبكة غير متزامن (Non-Blocking)
    return {"user_id": 101}

async def fetch_orders_data():
    await asyncio.sleep(1)
    return [{"order_id": 5001}]

async def fetch_analytics_data():
    await asyncio.sleep(1)
    return {"status": "active"}

async def main_async():
    start_time = time.perf_counter()

    # تنفيذ جميع المهام بالتوازي وبكفاءة عبر asyncio.gather
    results = await asyncio.gather(
        fetch_user_data(),
        fetch_orders_data(),
        fetch_analytics_data()
    )

    elapsed = time.perf_counter() - start_time
    print(f"نتائج الاستعلام: {results}")
    print(f"Async Total Execution Time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main_async())
```

### 4. الأدوات المتقدمة في مكتبة `asyncio` الإنتاجية (Production Grade)

#### أ. المهام الخلفية الموازية (Fire and Forget): `asyncio.create_task`

تُستخدم لبدء تشغيل مهمة في الخلفية دون تعطيل الرد على المستخدم (مثل إرسال الإيميلات أو تسجيل الـ Logs).

```python
import asyncio

async def send_welcome_email(user_email: str):
    await asyncio.sleep(2)  # محاكاة إرسال البريد
    print(f"Welcome email successfully sent to {user_email}")

async def register_user_endpoint():
    # بدء إرسال الإيميل في الخلفية دون تعطيل استجابة العميل
    email_task = asyncio.create_task(send_welcome_email("user@example.com"))

    # إرجاع الاستجابة فوراً للمستخدم (Latency شبه معدوم)
    print("User registered successfully!")

    # في البيئة الحقيقية (FastAPI BackgroundTasks تقوم بهذا الدور تلقائياً)
    await email_task

asyncio.run(register_user_endpoint())
```

#### ب. الحماية المعمارية عبر المهلات الزمنية: `asyncio.wait_for`

تمنع انهيار السيرفر أو استهلاك الذاكرة (Memory Leaks) إذا تعطل السيرفر الخارجي الذي تتصل به (مثل بوابات الدفع).

```python
import asyncio

async def slow_payment_gateway():
    await asyncio.sleep(5)  # بوابة دفع تواجه مشاكل وبطيئة جداً
    return {"status": "paid"}

async def process_checkout():
    try:
        # حماية السيرفر: إلغاء العملية واستثناء خطأ إذا تجاوزت ثانيتين
        result = await asyncio.wait_for(slow_payment_gateway(), timeout=2.0)
        print(f"Payment status: {result}")
    except asyncio.TimeoutError:
        print("Payment gateway timed out! Rolling back database transaction safely.")

asyncio.run(process_checkout())
```

### 5. الأخطاء المعمارية القاتلة في الإنتاج (Common Pitfalls & Best Practices)

#### 1. حظر حلقة الأحداث (Blocking the Event Loop):

- **الخطأ الكارثي:** استخدام مكتبات متزامنة مثل `requests.get()` أو `psycopg2` أو `time.sleep()` داخل دالة `async def`. هذه المكتبات توقف الـ Event Loop بالكامل، مما يعني تجميد السيرفر بأكمله عن الرد على **جميع المستخدمين الآخرين**.
- **الحل المعماري:** استخدام البدائل غير المتزامنة (Asynchronous Drivers) دائماً:
  - للشبكات و REST APIs: استخدم `httpx` بدلاً من `requests`.
  - لقواعد البيانات: استخدم `asyncpg` مع `SQLAlchemy AsyncSession` بدلاً من `psycopg2`.

#### 2. ترويض الكود المتزامن الإجباري: `asyncio.to_thread`

إذا اضطررت لاستخدام مكتبة خارجية (Legacy) لا تدعم الـ Async، يجب عزلها في Thread منفصل لحماية الـ Event Loop:

```python
import asyncio
import requests  # مكتبة متزامنة (Blocking)

def blocking_external_call():
    response = requests.get("https://api.github.com")
    return response.status_code

async def safe_async_wrapper():
    # تفويض تنفيذ الدالة المتزامنة إلى Thread Worker آمن
    status_code = await asyncio.to_thread(blocking_external_call)
    print(f"GitHub Status Code: {status_code}")

asyncio.run(safe_async_wrapper())
```

### الكبسولة المعمارية (Architectural Checklist)

1. **`async def` + `await`:** لا تضع `async` على دالة لا تحتوي على عمليات I/O، ولا تنسَ `await` عند مناداة دالة `async` أخرى.
2. **استغلال التوازي:** إذا كان لديك استعلامات مستقلة، استخدم `asyncio.gather()` لتنفيذها في الوقت نفسه بدلاً من التتابع.
3. **التدقيق الصارم:** راجع الكود للتأكد من عدم تسرب أي مكتبة blocking إلى endpoints غير المتزامنة.
""",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/rfscVS0vtbw",
            },
            {
                "title": "بناء واجهات API باستخدام FastAPI",
                "description": "تعلّم تنظيم مشروع FastAPI وبناء endpoints واضحة مع dependency injection والتوثيق التلقائي واختبارات تغطي الاستجابات والأخطاء.",
                "content": """
### 1. ثورة FastAPI في عالم الباك إند: لماذا هو الخيار الأول؟

لم يعد بناء واجهات برمجة التطبيقات (APIs) مجرد كتابة مسارات (Routes) تُرجع بيانات. في الأنظمة الحديثة، نحتاج إلى السرعة، التحقق الصارم من البيانات، والتوثيق الآلي. هنا يتربع **FastAPI** على العرش.

بُني FastAPI على عملاقين في عالم بايثون:
1. **Starlette:** لإدارة الـ Web Parts والعمليات غير المتزامنة (Async/Await) بسرعة تضاهي NodeJS و Go.
2. **Pydantic:** للتحقق من صحة البيانات (Data Validation) والـ Type Hinting بشكل صارم.

---

### 2. التشريح المعماري للـ Endpoints

يتكون أي مسار (Endpoint) احترافي من ثلاثة أجزاء رئيسية:
* **Path Parameters:** المتغيرات المدمجة في الرابط الأساسي (تُستخدم عادة لجلب مورد محدد عبر الـ ID).
* **Query Parameters:** المتغيرات المضافة بعد علامة `?` في الرابط (تُستخدم للفلترة، الترتيب، والبحث).
* **Request Body (Payload):** البيانات المرسلة في جسم الطلب (عادة مع POST و PUT) ويتم التحقق منها عبر نماذج Pydantic.

#### مثال عملي متكامل (CRUD Endpoint):

```python
from fastapi import FastAPI, Path, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="Kodraq Digital API",
    description="Production-grade API built with FastAPI",
    version="1.0.0"
)

# 1. تعريف نموذج البيانات (Pydantic Schema)
class UserCreate(BaseModel):
    username: str
    email: str
    is_active: bool = True

class UserResponse(UserCreate):
    id: int

# 2. بناء مسار GET مع Path & Query Parameters
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., title="The ID of the user", ge=1),
    include_details: bool = Query(False, description="Include full user history")
):
    # محاكاة الاستعلام من قاعدة البيانات
    if user_id != 101:
        raise HTTPException(status_code=404, detail="User not found in the database")

    return {"id": user_id, "username": "ahmed_morsi", "email": "ahmed@example.com"}

# 3. بناء مسار POST مع Request Body
@app.post("/users/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    # محاكاة حفظ البيانات وإرجاعها مع ID
    return {"id": 102, **user.model_dump()}
```

### 3. حقن الاعتمادات (Dependency Injection)

يعتبر الـ **Dependency Injection (DI)** من أقوى ميزات FastAPI، حيث يسمح لك بتمرير كائنات معقدة (مثل جلسات قاعدة البيانات، أو دوال التحقق من المستخدم) إلى الـ Endpoints بسهولة تامة، مما يجعل الكود قابلاً للاختبار (Testable) وإعادة الاستخدام (Reusable).

#### كيف نستخدم الـ DI للاتصال بقاعدة البيانات؟

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from database import SessionLocal

# دالة مساعدة (Dependency) لفتح وإغلاق جلسة قاعدة البيانات بأمان
def get_db():
    db = SessionLocal()
    try:
        yield db  # تسليم الجلسة للـ Endpoint
    finally:
        db.close()  # ضمان إغلاق الجلسة حتى لو حدث خطأ

# استخدام الـ Dependency في الـ Endpoint
@app.get("/analytics/")
async def fetch_analytics(db: Session = Depends(get_db)):
    # الآن db هي جلسة نشطة يمكن استخدامها بأمان
    data = db.execute("SELECT * FROM analytics").fetchall()
    return {"status": "success", "data": data}
```

### 4. التوثيق التلقائي (Automatic API Documentation)

أحد أكبر أسباب شهرة FastAPI هو توليده لتوثيق تفاعلي فوري يعتمد على معايير **OpenAPI**. بمجرد تشغيل السيرفر، يمكنك زيارة:

- `http://localhost:8000/docs` (تفاعلي عبر Swagger UI).
- `http://localhost:8000/redoc` (توثيق عميق ومفصل عبر ReDoc).

💡 **نصيحة إنتاجية:** استخدم دائماً `response_model` في الـ Decorator وقم بكتابة `docstrings` واضحة تحت تعريف الدالة لضمان ظهور التوثيق لفريق العمل بوضوح تام.

### 5. تنظيم المشروع للإنتاج (Project Routers)

لا تضع كل مساراتك في ملف `main.py`. في البيئات الإنتاجية، نستخدم `APIRouter` لتقسيم التطبيق إلى وحدات (Modules) مستقلة:

```python
# في ملف: routers/users.py
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users Management"])

@router.get("/")
async def list_users():
    return [{"name": "Ahmed"}, {"name": "Morsi"}]

# في ملف: main.py
from fastapi import FastAPI
from routers import users

app = FastAPI()

# ربط ملفات الروابط بالتطبيق الأساسي
app.include_router(users.router)
```

### 💡 الكبسولة المعمارية للدرس:

- اعتمد بشكل أساسي على `Pydantic` للتحقق من البيانات الواردة والصادرة.
- استخدم `Depends()` دائماً لإدارة جلسات قاعدة البيانات (Database Sessions) ومعالجة المصادقة (Authentication).
- قسّم تطبيقك باستخدام `APIRouter` لضمان قابلية التوسع والصيانة الدورية للمشروع.
""",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/iWS9ogMPOI0",
            },
            {
                "title": "التحقق من البيانات باستخدام Pydantic V2",
                "description": "افهم نماذج Pydantic V2 وحقولها المقيدة وعمليات serialization والتحقق المخصص لبناء حدود آمنة بين API وبيانات التطبيق.",
                "content": """
### 1. ثورة Pydantic V2: لماذا تمت إعادة كتابته بلغة Rust؟

في الإصدار الثاني (V2)، انتقل **Pydantic** إلى محرك تحقق وتسلسل مكتوب بلغة **Rust** اسمه `pydantic-core`. يبني Pydantic مخططاً داخلياً للحقول والقيود، ثم ينفذ المحرك التحقق والتحويل بكفاءة؛ وتشير المقارنات المنشورة إلى تحسن قد يصل إلى **5 إلى 50 ضعفاً** في بعض الحالات، بينما تعتمد النتيجة الفعلية على شكل البيانات والنموذج وطريقة القياس.

**دور Pydantic في المعمارية:**
يعمل Pydantic كحارس بوابة (Gatekeeper) صارم بين العالم الخارجي (طلبات المستخدمين) وعالمك الداخلي (قاعدة البيانات والمنطق البرمجي). لا توجد بيانات تدخل نظامك أو تخرج منه دون المرور على فلاتر Pydantic.

---

### 2. بناء النماذج الصارمة (Strict Models & Fields)

نستخدم `BaseModel` لتعريف هياكل البيانات، و `Field` لإضافة قيود دقيقة (Constraints) لا يمكن اختراقها.

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserRegistration(BaseModel):
    # استخدام Field لفرض قيود على طول النص واسم المستخدم
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')

    # EmailStr للتحقق التلقائي من صيغة البريد الإلكتروني (يتطلب pydantic[email])
    email: EmailStr

    # حقل اختياري مع قيمة افتراضية وقيود رقمية (العمر بين 18 و 100)
    age: Optional[int] = Field(None, ge=18, le=100)

    # حقل مخفي عن المستخدم يتم توليده تلقائياً
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. عمليات التحقق المتقدمة (Custom Validators)

ماذا لو أردنا التحقق من منطق معقد لا يمكن لـ `Field` تغطيته؟ هنا نستخدم `@field_validator` للتحقق من قيمة حقل واحد، و `@model_validator` لقواعد تعتمد على النموذج أو أكثر من حقل. يدعم `@field_validator` أوضاع `before` و `after` و `plain` و `wrap`؛ أما `@model_validator` فيستخدم `before` لفحص مدخلات النموذج الخام، و `after` للتحقق من النموذج بعد تحليل حقوله. ارفع `ValueError` عند مخالفة القاعدة ليحوّلها Pydantic إلى خطأ تحقق منظم.

```python
from pydantic import BaseModel, field_validator, model_validator

class PasswordReset(BaseModel):
    password: str
    confirm_password: str

    # 1. التحقق من قوة كلمة المرور (حقل واحد)
    @field_validator('password')
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        if len(value) < 8 or not any(char.isdigit() for char in value):
            raise ValueError('Password must be at least 8 characters and contain a number')
        return value

    # 2. التحقق من تطابق كلمتي المرور (على مستوى النموذج ككل)
    @model_validator(mode='after')
    def check_passwords_match(self) -> 'PasswordReset':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
```

### 4. التصدير والتسلسل (Serialization)

بعد التحقق من البيانات، ستحتاج إلى تصديرها للتعامل مع قاعدة البيانات (SQLAlchemy) أو إرسالها كاستجابة (JSON). Pydantic V2 يقدم طرقاً فائقة السرعة لذلك:

```python
user = UserRegistration(username="ahmed_morsi", email="ahmed@example.com")

# 1. التصدير إلى قاموس Python (Dictionary)
user_dict = user.model_dump()
# يمكنك استبعاد حقول معينة
safe_dict = user.model_dump(exclude={"created_at"})

# 2. التصدير مباشرة إلى JSON (فائق السرعة بفضل Rust)
json_data = user.model_dump_json()

# 3. التفريغ أثناء الاستجابة مع إخفاء البيانات الحساسة
public_data = user.model_dump(exclude_unset=True)
```

### 5. التكامل السحري مع FastAPI

في FastAPI، لا تحتاج لاستدعاء دوال التحقق يدوياً؛ بمجرد تعريف `Pydantic Schema` كنوع (Type Hint) في مسار (Endpoint)، يقوم FastAPI بالباقي:

1. يقرأ الـ JSON من الطلب.
2. يحوله لنموذج Pydantic ويتحقق من صحته.
3. إذا فشل التحقق، يُرجع رسالة خطأ 422 Unprocessable Entity واضحة جداً للمستخدم.
4. يولد توثيق OpenAPI يعرض القيود التي وضعتها في `Field`.

```python
from fastapi import FastAPI, HTTPException
app = FastAPI()

@app.post("/register/")
async def register(user: UserRegistration):
    # إذا وصل الكود إلى هذا السطر، فالبيانات مضمونة 100%
    return {"message": "User successfully registered", "data": user.model_dump()}
```

### الكبسولة المعمارية:

- **لا تثق ببيانات العميل أبداً:** اجعل Pydantic الخط الدفاعي الأول في تطبيقك.
- **استخدم `Field` بكثافة:** كلما أضفت قيوداً (`min_length`, `pattern`)، زادت قوة الـ API الخاص بك وتوثيقه.
- **احذر من `model_dump()` العشوائي:** استخدم خيارات مثل `exclude` لمنع تسريب بيانات حساسة (مثل كلمات المرور) في ردود السيرفر.
""",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/7aBRk_JP-qY",
            },
        ],
    },
    {
        "title": "Module 2: قواعد البيانات وإدارة التخزين المتقدمة",
        "description": "يركز هذا المسار على تصميم PostgreSQL، وبناء طبقة ORM باستخدام SQLAlchemy، وإدارة تغييرات المخطط والبيانات باستخدام Alembic.",
        "ordering": 2,
        "lessons": [
            {
                "title": "تصميم قواعد بيانات PostgreSQL والعلاقات",
                "description": "تعرّف تحويل متطلبات المنتج إلى مخطط PostgreSQL سليم باستخدام التطبيع والمفاتيح والعلاقات والقيود والفهارس المناسبة.",
                "content": """
### 1. هندسة قواعد البيانات العلائقية: من متطلبات المنتج إلى المخطط (Schema Design)

عند تصميم نظام خلفي (Backend) قابل للتوسع (Scalable)، تُعد قاعدة البيانات هي الأساس الصلب الذي يُبنى عليه كل شيء. تصميم قاعدة بيانات سيء يعني بطئاً كارثياً في الاستعلامات (Queries) وانهيار النظام تحت الضغط.

**مراحل تحويل المتطلبات إلى قواعد بيانات:**
1. **تحليل الكيانات (Entities):** تحديد العناصر الأساسية في النظام (مثل: المستخدمين `Users`، المنتجات `Products`، الطلبات `Orders`).
2. **تحديد الخصائص (Attributes):** استخراج أعمدة كل جدول وأنواع البيانات بدقة (`UUID`, `VARCHAR`, `TIMESTAMPTZ`, `JSONB`).
3. **التطبيع (Normalization - 1NF, 2NF, 3NF):** منع تكرار البيانات (Data Redundancy) لضمان سلامة البيانات ومنع حدوث أخطاء التحديث (Anomalies).

---

### 2. القيود الصارمة والمفاتيح (Keys & Constraints)

لضمان سلامة البيانات (Data Integrity)، لا يعتمد المطور المحترف على كود التطبيق وحده، بل يفرض القواعد على مستوى قاعدة البيانات نفسها:

* **Primary Key (PK):** المعرف الفريد لكل صف (يوصى بشدة باستخدام `UUIDv7` أو `BIGSERIAL` للأداء العالي).
* **Foreign Key (FK):** لربط الجداول ببعضها مع تفعيل قواعد الحذف التلقائي (`ON DELETE CASCADE` أو `SET NULL`).
* **Constraints الشهيرة:**
    * `NOT NULL`: منع القيم الفارغة في الأعمدة الأساسية.
    * `UNIQUE`: منع تكرار القيم (مثل البريد الإلكتروني أو اسم المستخدم).
    * `CHECK`: فرض شروط منطقية (مثل `CHECK (price >= 0)`).

```sql
-- مثال عملي: إنشاء جدول مستخدمين وطلبات بقيود صارمة وعلاقات
CREATE TABLE users (
        id BIGSERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        total_amount NUMERIC(10, 2) CHECK (total_amount >= 0),
        status VARCHAR(50) DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 3. أنواع العلاقات المعمارية (Relationships)

في PostgreSQL، تُدار العلاقات بين الجداول عبر ثلاثة أنواع رئيسية:

1. **One-to-Many (1:N):** العلاقة الأكثر شيوعاً (مثل: مستخدم واحد لديه عدة طلبات). يتم تخزين الـ Foreign Key في الجدول التابع (Many).
2. **Many-to-Many (N:M):** (مثل: الطلاب والمقررات الدراسية، أو المنتجات وCategories). تتطلب إنشاء جدول وسيط (Junction / Association Table).
3. **One-to-One (1:1):** نادرة الاستخدام، وتُلجأ إليها لفصل البيانات الحساسة أو الكبيرة (مثل: ملف شخصي للمستخدم `User Profile`).

### 4. الفهارس وتحسين الأداء (Indexing & Query Optimization)

بدون الفهارس (Indexes)، ستقوم قاعدة البيانات بعملية بحث كاملة عن الجدول (Sequential Scan) لكل طلب، مما يتسبب في بطء مدمّر مع نمو البيانات.

- **B-Tree Index:** الفهرس الافتراضي والأكثر استخداماً للبحث السريع عن البيانات (مقارنات المساواة والنطاقات مثل `>`, `<`, `=`).
- **GIN / GiST Indexes:** مخصص للبيانات المعقدة مثل النصوص الكاملة (Full-Text Search) وحقول `JSONB` في PostgreSQL.

#### تحليل خطة الاستعلام عبر `EXPLAIN ANALYZE`:

قبل نشر أي استعلام ضخم للإنتاج، يجب فحصه لمعرفة ما إذا كان المحرك يستفيد من الفهارس أم لا:

```sql
-- تحليل أداء الاستعلام ومعرفة وقت التنفيذ الفعلي
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE user_id = 42 AND status = 'pending';
```

### الكبسولة المعمارية للدرس:

1. **صمم بحكمة:** خطط للجداول والعلاقات على الورق أو باستخدام أدوات النمذجة قبل كتابة سطر كود واحد.
2. **استخدم القيود:** لا تترك حماية البيانات لكود بايثون وحده؛ قاعدة البيانات هي خط الدفاع الأخير.
3. **فهرس بذكاء:** أضف Indexes للأعمدة التي يتم البحث أو الترتيب بها متكرراً، وتجنب الإفراط في الفهارس لأنها تبطئ عمليات الـ `INSERT` و `UPDATE`.
""",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/ztv704HgWh0",
            },
            {
                "title": "نماذج SQLAlchemy وإدارة الجلسات",
                "description": "استخدم SQLAlchemy ORM والعلاقات وواجهة select في الإصدار 2.x مع ضبط عمر Session وحدود المعاملات وتجنب استعلامات N+1.",
                "content": """
### 1. مقدمة في SQLAlchemy 2.x ORM: جسر الكائنات العلائقية

تُعتبر مكتبة **SQLAlchemy** الأداة الأقوى في إيكوسيستم بايثون للتفاعل مع قواعد البيانات العلائقية. في الإصدار الثاني (`SQLAlchemy 2.x`)، تم تحديث النمط البرمجي بالكامل ليصبح أكثر توافقاً مع Type Hinting، وأكثر سرعة ووضوحاً (مماثل للنمط الحديث في FastAPI).

**مفهوم الـ ORM (Object Relational Mapping):**
هو تحويل الجداول والأعمدة في قاعدة البيانات إلى كائنات (Classes and Attributes) وفئات بايثون، مما يتيح لك كتابة استعلامات قاعدة البيانات بلغة بايثون الخالصة بدلاً من كتابة كود SQL يدوياً لكل عملية.

---

### 2. بناء النماذج الحديثة (Declarative Models with Mapped)

في SQLAlchemy 2.x، نستخدم النمط الحديث المعتمد على `Mapped` و `mapped_column` لتعريف الجداول والعلاقات بصرامة تامة:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, func
from datetime import datetime
from typing import List, Optional

# 1. القاعدة الأساسية للنماذج
class Base(DeclarativeBase):
    pass

# 2. نموذج المستخدم (User Model)
class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # العلاقة العكسية مع الطلبات (One-to-Many)
    orders: Mapped[List["OrderModel"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

# 3. نموذج الطلبات (Order Model)
class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # ربط الطلب بصاحبه
    owner: Mapped["UserModel"] = relationship(back_populates="orders")
```

### 3. إدارة الجلسات والمعاملات (Session Management & Transactions)

تُعد الـ `Session` هي المساحة البرمجية المؤقتة التي تتابع التغييرات على الكائنات وتدير دورة حياة المعاملات (Transactions).

#### إعداد الـ Engine و SessionLocal:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
```

#### التعامل مع المعاملات (Commit & Rollback بأمان):

يجب دائماً استخدام `try...except...finally` أو السياق الآمن (Context Manager) لضمان التراجع عن التغييرات (`rollback`) عند حدوث أي خطأ:

```python
def create_new_user(email: str, password_hash: str):
    session = SessionLocal()
    try:
        new_user = UserModel(email=email, hashed_password=password_hash)
        session.add(new_user)
        session.commit()  # حفظ التغييرات في قاعدة البيانات
        session.refresh(new_user)  # تحديث الكائن لجلب الـ ID المُولّد
        return new_user
    except Exception as e:
        session.rollback()  # إلغاء المعاملة حال حدوث خطأ لمنع تضارب البيانات
        raise e
    finally:
        session.close()  # إغلاق الجلسة وتحرير الموارد
```

### 4. استراتيجيات الجلب وتجنب مشكلة N+1 (Loading Strategies)

واحدة من أكبر مشاكل الأداء في الـ ORM هي **مشكلة استعلامات N+1**؛ حيث يتم جلب المستخدمين في استعلام، ثم يتم تنفيذ استعلام منفصل لكل مستخدم لجلب طلباته، مما يقتل أداء السيرفر.

**الحل عبر استخدام استراتيجيات التحميل المسبق (Eager Loading):**

- **`selectinload`:** الأفضل والأكثر كفاءة لعلاقات (One-to-Many). يقوم بجلب البيانات المرتبطة في استعلام منفصل باستخدام جملة `IN (...)`.
- **`joinedload`:** يقوم بجلب البيانات في نفس الاستعلام عبر جملة `SQL JOIN`.

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

def get_users_with_orders(session):
    # استخدام select الحديثة مع selectinload لتجنب مشكلة N+1
    stmt = select(UserModel).options(selectinload(UserModel.orders))
    result = session.scalars(stmt).all()
    return result
```

### الكبسولة المعمارية للدرس:

1. **استخدم SQLAlchemy 2.x Style:** اعتمد على `Mapped` و `mapped_column` للحصول على أفضل دعم للـ Type Hinting واكتشاف الأخطاء مبكراً.
2. **أغلق الجلسات دائماً:** تأكد من إغلاق الـ Session بعد انتهاء الطلب لتجنب استنزاف اتصالات قاعدة البيانات (Connection Pool Leaks).
3. **راقب الاستعلامات:** استخدم `selectinload` عند جلب جداول مرتبطة لمنع الوقوع في فخ استعلامات N+1 المدمرة للأداء.
""",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/AbN1AEm_98s",
            },
            {
                "title": "ترحيل المخطط باستخدام Alembic و SQLAlchemy",
                "description": "أنشئ migrations قابلة للمراجعة والتكرار، وطبق تغييرات المخطط والبيانات بأمان عبر بيئات التطوير والاختبار والإنتاج.",
                "content": """
### 1. إدارة التغيرات المعمارية: لماذا نحتاج إلى Alembic؟

عندما يتطور مشروعك البرمجي، ستتغير هياكل الجداول (Schemas) باستمرار: إضافة أعمدة جديدة، تعديل أنواع البيانات، أو إنشاء جدول جديد. التعديل اليدوي في قاعدة البيانات (Direct SQL Alter) يعتبر انتحاراً معمارياً في بيئة الإنتاج (Production).

هنا يأتي دور **Alembic**؛ أداة إدارة وترحيل المخططات (Database Migrations) الرسمية لـ SQLAlchemy، والتي تتيح لك:
1. تتبع كل تغيير يطرأ على قاعدة البيانات عبر إصدارات (Revisions).
2. تطبيق التغييرات (`upgrade`) أو التراجع عنها (`downgrade`) بكل أمان وسلاسة.
3. مزامنة هيكل قاعدة البيانات بدقة بين أفراد فريق العمل وفي سيرفرات الإنتاج.

---

### 2. تهيئة وإعداد Alembic في المشروع

لبدء استخدام Alembic داخل مشروع FastAPI والـ SQLAlchemy، نمر بخطوات التأسيس التالية عبر الـ Terminal:

```bash
# 1. تثبيت الحزمة عبر الأداة pip
pip install alembic

# 2. تهيئة المجلد الخاص بـ Alembic في مشروعك
alembic init alembic
```

ينتج عن ذلك مجلد `alembic/` وملف إعدادات رئيسي `alembic.ini`. لتفعيل الاتصال بنماذج SQLAlchemy الخاصة بك، يجب تعديل ملف `alembic/env.py` ليشير إلى قاعدة البيانات ونماذج `Base`:

```python
# داخل ملف alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# استيراد Base النماذج الخاصة بك لتتعرف Alembic على الجداول
from database import Base
target_metadata = Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ربط عنوان قاعدة البيانات من ملفات الإعدادات أو البيئة
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_section_name, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 3. دورة حياة الترحيل: Auto-generation & Execution

بعد تعديل نماذج بايثون (إضافة جدول جديد أو عمود)، قم بتوليد ملف الـ Migration تلقائياً وتطبيقه عبر الأوامر التالية:

```bash
# 1. توليد ملف ترحيل جديد بناءً على التغييرات في النماذج
alembic revision --autogenerate -m "add user phone and status columns"

# 2. تطبيق التغييرات على قاعدة البيانات الفعليّة (Production / Dev)
alembic upgrade head

# 3. في حال حدوث مشكلة، التراجع عن آخر ترحيل خطوة للوراء
alembic downgrade -1
```

### 4. التعامل الآمن مع البيانات (Data Migrations)

أحياناً لا تقتصر التغييرات على الهيكل، بل تتطلب معالجة بيانات موجودة (مثلاً دمج عمودين `first_name` و `last_name` في عمود واحد `full_name`). في هذه الحالات، يجب كتابة كود الترحيل اليدوي داخل ملف الـ Revision المولد:

```python
from alembic import op
import sqlalchemy as sa

# مراجعة الـ upgrade والـ downgrade المكتوبة يدوياً
def upgrade() -> None:
    # إضافة عمود جديد مؤقتاً
    op.add_column('users', sa.Column('full_name', sa.String(100), nullable=True))

    # تنفيذ تحديث للبيانات القديمة عبر SQL مباشر داخل الترحيل
    op.execute("UPDATE users SET full_name = first_name || ' ' || last_name")

    # حذف الأعمدة القديمة بعد ترحيل البيانات بنجاح
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')

def downgrade() -> None:
    # عكس العملية في حال التراجع
    op.add_column('users', sa.Column('first_name', sa.String(50)))
    op.add_column('users', sa.Column('last_name', sa.String(50)))
    op.execute("UPDATE users SET first_name = split_part(full_name, ' ', 1), last_name = split_part(full_name, ' ', 2)")
    op.drop_column('users', 'full_name')
```

### الكبسولة المعمارية للدرس:

1. **لا تعبث بقاعدة البيانات يدوياً:** اجعل كل التغييرات تمر عبر ملفات `Alembic Revisions` لتكون موثقة وقابلة للتكرار.
2. **راجع ملف الترحيل قبل تنفيذه:** أحياناً تفشل الأداة في رصد بعض التغييرات الدقيقة تلقائياً (مثل تغيير اسم عمود)، لذا افحص ملف الـ Migration الناتج دائماً قبل `alembic upgrade head`.
3. **احذر في بيئة الإنتاج:** قم بأخذ نسخة احتياطية (Backup) لقاعدة البيانات قبل تنفيذ أي عمليات Migration ضخمة على سيرفر الإنتاج الحقيقي.
""",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/k7u02qb8lXg",
            },
        ],
    },
    {
        "title": "Module 3: هندسة الذكاء الاصطناعي وتكامل أنظمة RAG",
        "description": "يقدم هذا المسار صياغة prompts لنماذج اللغة، والبحث المتجهي باستخدام pgvector، وبناء خط RAG كامل متصل بخدمة الباك إند.",
        "ordering": 3,
        "lessons": [
            {
                "title": "نماذج اللغة الكبيرة وهندسة Prompt Engineering",
                "description": "تعرّف كفاءات وقيود نماذج اللغة الكبيرة، وكيفية صياغة prompts احترافية، وتطبيق تقنيات Few-Shot و Chain-of-Thought.",
                "content": """
### 1. ما هي نماذج اللغة الكبيرة (LLMs)؟ وكيف تعمل تحت Hood؟

تعمل نماذج اللغة الكبيرة (Large Language Models مثل GPT-4 و Claude 3) على مبدأ أساسي واحد: **التنبؤ بالرمز التالي (Next-Token Prediction)** بناءً على السياق السابق. وعلى الرغم من بساطة الفكرة، فإن ضخامة عدد المعاملات (Parameters) والبيانات تمنح هذه النماذج قدرات لغوية واستدلالية واسعة.

**القيود الجوهرية للـ LLMs:**
* **الهلوسة (Hallucinations):** قد يولد النموذج إجابات تبدو مقنعة لكنها خاطئة أو غير مدعومة؛ فهو لا يتحقق من الحقيقة تلقائياً.
* **الحسابات الدقيقة:** النماذج ليست آلات حاسبة، وقد تخطئ في الحساب؛ استخدم أدوات تنفيذ أو Function Calling عندما تكون الدقة الحسابية مطلوبة.
* **نافذة السياق (Context Window):** حد لكمية الرموز التي يمكن للنموذج معالجتها في الطلب الواحد، ويؤثر في اختيار الأمثلة والمستندات المرسلة.

---

### 2. هندسة الأوامر الاحترافية (Prompt Engineering Frameworks)

للحصول على نتائج دقيقة وقابلة للاستخدام في الأنظمة البرمجية، هيكل الـ Prompt بوضوح:

1. **الدور (Role / Persona):** حدّد خبرة النموذج والمهمة، مثل `You are an expert backend engineer and security auditor`.
2. **السياق (Context):** قدّم خلفية المشكلة والبيانات المتاحة ومصادرها.
3. **التعليمات (Instructions):** اشرح المطلوب، والخطوات أو المعايير التي يجب اتباعها.
4. **محددات المخرجات (Output Format):** حدّد الطول والبنية، مثل Markdown أو مخطط JSON واضح.
5. **التحقق (Evaluation):** اختبر prompt على أمثلة عادية وحدّية، وقِس الدقة والالتزام بالمخطط.

#### مثال عملي لـ Structured Prompt:

```text
System:
You are a senior API architect. Review the provided FastAPI endpoint code for security vulnerabilities.

Context:
The application handles user financial transactions.

Instructions:
1. Identify any SQL injection or authentication flaws.
2. Provide a severity score (Low, Medium, High) for each flaw.
3. Output the result strictly in valid JSON format.

Input Code:
@app.get("/balance")
def get_balance(user_id: str):
    query = f"SELECT * FROM accounts WHERE id = {user_id}"
    return db.execute(query).fetchall()
```

### 3. تقنيات الاستدلال المتقدمة (Advanced Prompting Techniques)

للمهام المعقدة، تساعد تقنيات prompting على تنظيم أمثلة النموذج أو خطوات استخدام الأدوات:

- **Few-Shot Prompting:** أعطِ النموذج أمثلة واضحة من المدخلات والمخرجات قبل السؤال النهائي لتوجيهه نحو النمط المطلوب.
- **Chain-of-Thought (CoT):** استخدمه لتنظيم حل المهام متعددة الخطوات، واطلب مبرراً موجزاً أو خلاصة تحقق مناسبة للمستخدم بدلاً من الاعتماد على عرض الاستدلال الداخلي دليلاً على الصحة.
- **ReAct (Reason + Act):** نسّق حلقة اختيار أداة ثم ملاحظة نتيجتها ومتابعة المهمة. امنح الأدوات صلاحيات محدودة، وتحقق من مدخلاتها ومخرجاتها قبل تنفيذ أي إجراء.

### 4. التحكم بالمخرجات عبر Structured Outputs

في تطبيقات الـ Backend، لا تعتمد على نصوص عشوائية من الـ LLM. استخدم JSON mode أو Structured Outputs مع مخطط مثل Pydantic، ثم تحقق من القيم قبل استخدامها؛ فسلامة الشكل لا تضمن صحة المعنى.

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class CodeReviewResponse(BaseModel):
    is_secure: bool
    vulnerabilities: list[str]
    recommendation: str

# طلب مخرجات تطابق مخطط Pydantic
completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Review this code..."}],
    response_format=CodeReviewResponse,
)

result = completion.choices[0].message.parsed
print(result.is_secure, result.vulnerabilities)
```

### الكبسولة المعمارية للدرس:

1. **لا تثق بالنصوص الحرة:** استخدم Structured Outputs (مثل Pydantic مع النماذج) للتحقق من توافق المخرجات مع عقد الـ Backend.
2. **نظّم المهام المعقدة:** استخدم Few-Shot أو تقنيات الاستدلال والأدوات المناسبة، ثم قيّم النتيجة النهائية باختبارات مستقلة.
3. **افصل التعليمات عن البيانات:** استخدم delimiters واضحة مثل `---` أو XML tags، وتعامل مع مدخلات المستخدم والمحتوى المسترجع كبيانات غير موثوقة للحد من Prompt Injection.
""",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/bAUvV1WTPzs",
            },
            {
                "title": "Embeddings والبحث المتجهي باستخدام pgvector",
                "description": "افهم تحويل النصوص إلى embeddings واستخدام PostgreSQL مع إضافة pgvector لإجراء بحث دلالي (Semantic Search) فائق السرعة.",
                "content": """
### 1. ما هي الـ Embeddings وكيف تتحول الكلمات إلى أرقام؟

في قواعد البيانات التقليدية، نبحث عن الكلمات بالمطابقة الحرفية (Keyword Search)، مما يعني أن البحث عن كلمة "شقة" لن يظهر نتائج تحتوي على "منزل" أو "سكن". هنا يأتي دور **Embeddings**.

الـ Embeddings هي تمثيل رياضي (Numerical Representation) للنصوص في شكل متجهات (Vectors) ذات أبعاد عالية (مثل 1536 بُعداً في بعض نماذج OpenAI).
* الكلمات أو الجمل ذات المعنى المتقارب تُترجم إلى متجهات قريبة من بعضها في الفضاء الرياضي (Vector Space).
* هذا ما يتيح لنا بناء **البحث الدلالي (Semantic Search)** الذي يفهم المعنى والقصد بغض النظر عن اختلاف الألفاظ.

---

### 2. تفعيل واستخدام `pgvector` في PostgreSQL

بدلاً من استخدام قواعد بيانات متجهية منفصلة، تتيح لنا إضافة **`pgvector`** في PostgreSQL تخزين المتجهات والبيانات العلائقية والبحث فيها ضمن قاعدة بيانات واحدة.

#### تفعيل الإضافة وإنشاء جدول للمتجهات:

```sql
-- 1. تفعيل الإضافة في قاعدة البيانات
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. إنشاء جدول يحتوي على أعمدة المتجهات
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536) -- يجب أن يطابق عدد الأبعاد نموذج التضمين المستخدم
);
```

### 3. مقاييس التشابه (Distance Metrics)

لحساب مدى تقارب متجه السؤال مع المستندات المخزنة، توفر `pgvector` ثلاثة مقاييس أساسية:

1. **Cosine Distance (`<=>`):** يقيس اختلاف اتجاه المتجهين، ويشيع استخدامه في البحث الدلالي.
2. **Inner Product (`<#>`):** يعيد الضرب الداخلي السالب في pgvector، ويُستخدم مع ترتيب تصاعدي؛ تحقّق من ملاءمته لتطبيع المتجهات ونموذج التضمين.
3. **Euclidean Distance (`<->`):** يقيس المسافة المباشرة بين نقطتين في الفضاء (L2 Distance).

اختر العامل المتوافق مع نموذج التضمين، وقيّم النتائج على عينة ممثلة من الاستعلامات بدلاً من افتراض أن مقياساً واحداً مناسب لكل البيانات.

#### تنفيذ استعلام البحث الدلالي:

```sql
-- البحث عن أقرب 5 مستندات شبهاً بمتجه السؤال
SELECT id, content,
       1 - (embedding <=> :query_embedding) AS similarity_score
FROM documents
ORDER BY embedding <=> :query_embedding
LIMIT 5;
```

### 4. تحسين الأداء والفهارس (Indexing: IVFFlat vs HNSW)

عندما يحتوي الجدول على ملايين المستندات، قد يصبح البحث الدقيق مكلفاً. توفر فهارس `pgvector` بحثاً تقريبياً يوازن بين زمن الاستجابة ودقة الاسترجاع:

- **IVFFlat (Inverted File with Flat Quantization):** يقسم فضاء المتجهات إلى قوائم، ثم يبحث في عدد مختار منها. يحتاج إلى بيانات مناسبة عند بناء الفهرس، ويمكن ضبط عدد القوائم والبحث لموازنة السرعة والاستدعاء.
- **HNSW (Hierarchical Navigable Small World):** يبني شبكة متعددة الطبقات للوصول بسرعة إلى متجهات قريبة، مع مقايضة في استهلاك الذاكرة ووقت بناء الفهرس.

أنشئ الفهرس باستخدام operator class المطابق لمقياس المسافة، ثم افحص الخطة ونتائج الاسترجاع على بيانات فعلية:

```sql
-- إنشاء فهرس HNSW لتسريع البحث بترتيب Cosine Distance
CREATE INDEX documents_embedding_hnsw_idx
ON documents
USING hnsw (embedding vector_cosine_ops);
```

### الكبسولة المعمارية للدرس:

1. **استفد من PostgreSQL:** يتيح `pgvector` الجمع بين البيانات العلائقية والبحث المتجهي، مع تقليل تعقيد تشغيل مخازن منفصلة عند ملاءمة ذلك لحجم النظام.
2. **اختر مقياس التشابه بحكمة:** استخدم Cosine Distance (`<=>`) عندما يناسب تمثيل النموذج، وتحقق من جودة النتائج.
3. **فهرس المتجهات وراقبها:** اختبر HNSW أو IVFFlat على حجم بيانات ممثل، ووازن بين زمن البحث والذاكرة ودقة الاسترجاع.
""",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/JXUS7i_tqxo",
            },
            {
                "title": "تصميم وتنفيذ بنية RAG متكاملة",
                "description": "تصميم وتنفيذ بنية RAG متكاملة تجمع بين البحث والدلالة واسترجاع البيانات من قاعدة البيانات لتغذية نماذج الذكاء الاصطناعي بدقة عالية.",
                "content": """
### 1. ما هو نظام RAG ولماذا نحتاج إليه؟

تعاني نماذج اللغة الكبيرة (LLMs) من مشكلتين رئيسيتين:
1. **القصور المعرفي:** لا تعرف النماذج تلقائياً بيانات شركتك الخاصة أو المستندات الداخلية الحديثة.
2. **الهلوسة:** قد تختلق النماذج إجابة تبدو مقنعة لكنها غير صحيحة أو غير مدعومة بمصدر.

يأتي **RAG (Retrieval-Augmented Generation)** ليجمع بين **البحث والاسترجاع (Retrieval)** و**التوليد بالذكاء الاصطناعي (Generation)**. يسترجع النظام مستندات حقيقية ذات صلة بسؤال المستخدم، ثم يمررها إلى النموذج كسياق يمكن الاستناد إليه عند صياغة الإجابة. تساعد الأدلة على تقليل الهلوسة (Hallucinations)، لكن RAG لا يضمن صحة الإجابة تلقائياً؛ فالموثوقية تعتمد على جودة البيانات والاسترجاع والتحقق.

---

### 2. خطوط إنتاج تجهيز البيانات (Ingestion Pipeline)

يجب تجهيز المستندات (PDFs, Docs, Database Records) بطريقة قابلة للتكرار قبل تخزينها واستخدامها:

1. **تقسيم النصوص (Chunking Strategies):** لا ترسل مستنداً كاملاً إلى النموذج. قسّم النص إلى مقاطع مناسبة لمحتواه، وأضف تداخلاً (Overlap) محسوباً لتقليل فقد السياق عند حدود المقاطع. اختبر أحجاماً مختلفة بدلاً من اعتماد عدد ثابت لكل أنواع المستندات.
2. **توليد التضمينات (Embedding Generation):** حوّل كل مقطع نصي (Chunk) إلى متجه باستخدام نموذج تضمين مثل `text-embedding-3-small`. سجّل إصدار النموذج والأبعاد لتجنب مقارنة متجهات غير متوافقة.
3. **التخزين في قاعدة البيانات:** احفظ النص الأصلي والمتجه ومعرف المصدر وبياناته الوصفية في PostgreSQL مدعوم بـ `pgvector`.
4. **التحديث وإعادة المعالجة:** اجعل ingestion قابلاً لإعادة المحاولة والتكرار، وحدد كيفية تحديث أو حذف المقاطع عند تغير المستند المصدر.

---

### 3. بنية الاسترجاع والبحث الهجين (Hybrid Search & Retrieval)

عندما يطرح المستخدم سؤالاً، يمر الاسترجاع عادة بالخطوات التالية:

1. تحقق من هوية المستخدم ونطاق البيانات التي يسمح له بالوصول إليها.
2. أنشئ Query Embedding للسؤال باستخدام النموذج المتوافق مع المتجهات المخزنة.
3. استرجع المرشحين بالبحث الدلالي (Semantic Search) عبر `pgvector`.
5. ادمج النتائج عند الحاجة مع بحث الكلمات المفتاحية أو PostgreSQL Full-Text Search لتكوين **Hybrid Search**.
6. أعد ترتيب النتائج (Context Re-ranking) باستخدام نموذج reranker أو Cross-Encoder لتحسين ترتيب المقاطع الأكثر صلة قبل بناء السياق.
5. أعد ترتيب المرشحين بحسب الصلة، ثم اختر عدداً محدوداً من المقاطع للسياق.

```python
from sqlalchemy import select

def retrieve_relevant_context(user_query: str, db_session, top_k: int = 4) -> str:
    query_vector = get_embedding(user_query)
    stmt = (
        select(DocumentModel)
        .where(DocumentModel.track_id == authorized_track_id)
        .order_by(DocumentModel.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    results = db_session.scalars(stmt).all()
    return "\n\n".join(document.content for document in results)
```

يجب اشتقاق `authorized_track_id` من صلاحيات المستخدم في الخادم، لا من قيمة يرسلها العميل دون تحقق. يمكن إدخال نتائج البحث النصي والمتجهي في مرحلة دمج وترتيب، ثم تمرير أفضل المقاطع فقط إلى النموذج.

### 4. التوليد الآمن ومنع الهلوسة (Generation & Anti-Hallucination)

أرسل السياق المسترجع مع السؤال ضمن تعليمات واضحة تطلب من النموذج الاعتماد على الأدلة، والإقرار بعدم كفاية السياق عند غياب الإجابة. عامل المستندات المسترجعة كمدخلات غير موثوقة؛ افصلها عن التعليمات، ولا تسمح لأي نص فيها بتغيير السياسات أو تنفيذ أدوات.

```python
def generate_rag_response(user_query: str, context: str):
    system_prompt = f'''You are a precise enterprise assistant. Answer the user's question using only the provided context.
If the answer is not supported by the context, state clearly that the documents do not contain it. Do not invent facts.

Context:
{context}
'''

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content
```

تحقق من المراجع والمخرجات قبل عرضها، وتعامل مع الرد الفارغ أو فشل النموذج أو غياب نتائج الاسترجاع بحالات واضحة في التطبيق.

### الكبسولة المعمارية للدرس:

1. **التقسيم الذكي هو السر:** قيّم حجم المقاطع والتداخل على أسئلة واقعية؛ فهما يؤثران في دقة الاسترجاع واكتمال السياق.
2. **استخدم البحث الهجين:** اجمع البحث الدلالي مع البحث النصي عند احتياج المجال للمطابقة الدقيقة وللتشابه في المعنى.
3. **قلّل الهلوسة بالأدلة والتحقق:** استخدم سياقاً مصرحاً وذا صلة، واطلب إجابة مقيدة به، ثم تحقق من المصادر والنتيجة في طبقة التطبيق.
""",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/sVqYi4WYXwY",
            },
        ],
    },
    {
        "title": "Module 4: النشر السحابي والتشغيل الإنتاجي - Module 04",
        "description": "جهّز تطبيق الباك إند للعمل الإنتاجي عبر إعداد الخادم وGunicorn/Uvicorn، ثم أتمتة الفحوصات والبناء والنشر إلى Vercel وRailway.",
        "ordering": 4,
        "lessons": [
            {
                "title": "تشغيل FastAPI و Uvicorn/Gunicorn للإنتاج",
                "description": "تعلم كيفية ضبط خادم Uvicorn و Gunicorn لإدارة العمال (Workers) والعمليات الإنتاجية المرتفعة الأداء والتوافر.",
                "content": """
### 1. من بيئة التطوير إلى بيئة الإنتاج: الفرق بين ASGI و WSGI

عند تطوير تطبيقات FastAPI محلياً، نعتمد عادةً على خادم **Uvicorn** بالخيار `--reload` لسرعة التطوير. لكن في بيئات الإنتاج الحقيقية (Production)، هذا الإعداد غير مناسب ولا يستغل موارد السيرفر بالشكل المطلوب.

* **WSGI (Web Server Gateway Interface):** واجهة تقليدية تستخدمها أطر مثل Django وFlask في نمطها المتزامن. يعتمد التوازي فيها غالباً على عمليات أو threads متعددة، لذلك يجب ضبط مواردها وفق حمل التطبيق.
* **ASGI (Asynchronous Server Gateway Interface):** واجهة غير متزامنة تعتمدها FastAPI، وتدعم اتصالات متزامنة عبر event loop عند استخدام مسارات ومكتبات غير حاجبة، مع إمكانية استخدام حلقات ومكتبات عالية الأداء مثل `uvloop` و`httptools`.

---

### 2. لماذا نحتاج Gunicorn بجانب Uvicorn؟ (Process Management)

يمكن تشغيل Uvicorn مباشرةً، لكنه يعمل افتراضياً بعملية واحدة. للاستفادة من عدة أنوية CPU يمكن استخدام مدير عمليات يشغّل عدة عمال:

1. إطلاق عدة عمليات Uvicorn Workers لخدمة الطلبات.
2. توزيع الاتصالات على العمليات ومراقبتها.
3. إعادة تشغيل العامل المتعطل وفق سياسة مدير العمليات، مع ضبط الإغلاق والمهلات لتقليل أثر الأعطال.

يمكن استخدام **Gunicorn** لإدارة هذه العمليات في البيئات التي تدعمه. يعتمد الاختيار بين مدير العمليات المدمج في منصة النشر وتشغيل Gunicorn على نظام التشغيل وطريقة النشر وإصدارات الحزم.

---

### 3. تقدير عدد العمال وإعداد التشغيل

تُستخدم المعادلة التالية كتقدير أولي فقط، وليست قاعدة ثابتة:

$$\\text{Workers} = (2 \\times \\text{Number of CPU Cores}) + 1$$

اضبط العدد بعد قياس استهلاك الذاكرة وCPU وزمن الاستجابة؛ فزيادة العمال قد ترفع استهلاك الذاكرة واتصالات قاعدة البيانات ولا تضمن تحسناً في الأداء.

#### مثال لأمر تشغيل عبر Terminal أو Docker:

```bash
# تحقّق من توافق مسار worker مع إصدار Uvicorn المستخدم
gunicorn main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 0.0.0.0:8000 \\
    --timeout 120 \\
    --max-requests 1000 \\
    --max-requests-jitter 50 \\
    --access-logfile - \\
    --error-logfile -
```

- `--max-requests`: إعادة تشغيل العامل بعد عدد محدد من الطلبات، كوسيلة احترازية وليست علاجاً لتسرب الذاكرة.
- `--max-requests-jitter`: إضافة تفاوت عشوائي لتقليل احتمال إعادة تشغيل كل العمال في الوقت نفسه.

### 4. الإغلاق الآمن وفحص الجاهزية (Graceful Shutdown & Health Checks)

في بيئات النشر السحابية، يجب أن يغلق التطبيق موارده عند تلقي إشارات الإيقاف (`SIGTERM` / `SIGINT`) بطريقة تسمح بإنهاء الطلبات الجارية وتحرير مجمعات الاتصالات:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
        # تهيئة الموارد عند بدء التطبيق
        print("Starting server and database connections")
        yield
        # تحرير الموارد عند إيقاف التطبيق
        print("Shutting down gracefully and cleaning up connection pools")

app = FastAPI(lifespan=lifespan)

@app.get("/healthz", status_code=200)
def health_check():
        return {"status": "healthy", "service": "Kodraq Backend"}
```

اجعل فحص الجاهزية يتحقق من الاعتماديات الضرورية عند الحاجة، ولا تكشف تفاصيل أو أسراراً داخل استجابة الفحص.

### الكبسولة المعمارية للدرس:

1. **لا تشغّل `--reload` في الإنتاج:** فهو مخصص للتطوير ويضيف مراقبة وإعادة تحميل غير لازمتين في التشغيل النهائي.
2. **اختر مدير العمليات المناسب:** استخدم Gunicorn مع worker متوافق، أو آلية العمال التي توفرها منصة التشغيل، واضبط العدد وفق القياس.
3. **وفر Health Checks دائماً:** أضف مسار `/healthz` وفحوصات جاهزية مناسبة حتى تتمكن منصة النشر من رصد حالة الخدمة والتعامل مع تعطلها.
""",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/71aB4oE52m0",
            },
            {
                "title": "إدارة متغيرات البيئة والأسرار والشهادات",
                "description": "تأمين التطبيق باستخدام Pydantic Settings وحفظ المفاتيح في متغيرات البيئة وركائز الأمن وحماية الاتصالات عبر SSL/TLS.",
                "content": """
### 1. إدارة الإعدادات الحديثة عبر Pydantic Settings

تُعد طبقة الإعدادات (Settings Management) خط الدفاع الأول في أي تطبيق إنتاجي. يجب إبعاد كافة المفاتيح الحساسة (مثل `DATABASE_URL` و`JWT_SECRET_KEY` ومفاتيح API الخاصة بـ OpenAI) عن الكود المصدري (Hardcoded Values).

في **FastAPI** و**Pydantic V2**، نستخدم مكتبة `pydantic-settings` لإدارة الإعدادات وقراءتها من متغيرات البيئة (Environment Variables) أو ملفات `.env` مع التحقق الصارم من أنواع البيانات (Type Validation):

```python
from functools import lru_cache

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Kodraq Platform"
    ENV: str = "production"

    # التحقق من صحة رابط قاعدة البيانات
    DATABASE_URL: PostgresDsn

    # SecretStr يخفي القيمة عند تمثيل الإعداد أو تسجيله
    JWT_SECRET_KEY: SecretStr
    OPENAI_API_KEY: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

### 2. إدارة المفاتيح السرية وحمايتها من التسريب (Secrets Protection)

تسريب المفاتيح السرية إلى المستودعات العامة هو أحد أسباب اختراق الأنظمة والتكلفة غير المتوقعة في الخدمات السحابية.

- **استخدام `.gitignore` بصرامة:** أضف `.env` و`.env.local` وملفات المفاتيح إلى `.gitignore`، ولا تعتمد على ذلك وحده لحماية أسرار بيئة الإنتاج.
- **استخدام `SecretStr` في Pydantic:** يخفي التمثيل الافتراضي القيمة الحساسة في السجلات، لكنه لا يمنع تسريبها إذا استخرجت القيمة صراحة أو أرسلتها إلى مكان غير آمن.
- **إدارة أسرار الإنتاج:** خزّن الأسرار في secret manager أو إعدادات منصة النشر، وقيّد صلاحيات الوصول، ودوّر المفاتيح عند الاشتباه بتسربها.

```python
# استخراج القيمة السرية فقط عند الحاجة إلى عميل API موثوق
api_key_value = settings.OPENAI_API_KEY.get_secret_value()
```

### 3. تأمين الاتصالات وسياسات CORS و SSL/TLS

في بيئات الإنتاج، استخدم HTTPS لحماية البيانات أثناء انتقالها بين الواجهة والخادم ومنع التنصت أو التلاعب بها (Man-in-the-Middle Attacks). أدر شهادات SSL/TLS وتجديدها عبر منصة النشر أو وكيل عكسي موثوق.

#### ضبط سياسات نفاذ المصادر المتقاطعة (CORS Management)

تتحكم CORS في أصول المتصفح المسموح لها بقراءة استجابات API. في الإنتاج، حدد النطاقات الموثوقة وتجنب `allow_origins=["*"]`، خصوصاً عند السماح بالاعتمادات:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://kodraq.com",
    "https://www.kodraq.com",
    "https://app.kodraq.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### الكبسولة المعمارية للدرس:

1. **لا تضع أسراراً في الكود أبداً:** اقرأ الإعدادات من متغيرات البيئة أو مخزن أسرار باستخدام `pydantic-settings`.
2. **احمِ السجلات من التسريبات:** استخدم `SecretStr`، وتجنب تسجيل قيم الأسرار أو تضمينها في رسائل الأخطاء.
3. **قيّد نطاقات CORS:** لا تستخدم النجمة `*` في `allow_origins` على خوادم الإنتاج؛ حدد نطاقات تطبيقك الرسمية فقط.
""",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/K1BIn3e6704",
            },
            {
                "title": "النشر السحابي على Vercel و Railway والربط بـ Supabase",
                "description": "نشر واجهات FastAPI والـ Frontend على منصات Vercel و Railway والربط الآمن بقاعدة بيانات PostgreSQL على Supabase.",
                "content": """
### 1. الإستراتيجية المعمارية لنشر التطبيقات الحديثة (Cloud Topology)

في المعماريات السحابية الحديثة، نعتمد على فصل الخدمات (Decoupled Architecture) لضمان الأداء والمرونة والتوسع المستقل:

* **قاعدة البيانات (Database Layer):** تُدار عبر **Supabase (Managed PostgreSQL)** مع دعم `pgvector` وConnection Pooling عند الحاجة.
* **الخلفية البرمجية (Backend API Layer):** يُنشر تطبيق FastAPI على **Railway** أو Render باستخدام حاويات **Docker** وعمليات تشغيل مستقرة.
* **الواجهة الأمامية (Frontend Web App):** تُنشر على **Vercel** للاستفادة من شبكة CDN وتحسين توصيل ملفات الواجهة.

---

### 2. الربط بقاعدة بيانات Supabase وإدارة Connection Pooling

قد تستنزف التطبيقات ذات الاتصالات المتوازية أو نماذج Serverless الحد الأقصى لاتصالات PostgreSQL. يوفر Supabase روابط اتصال مباشرة وروابط عبر Transaction Pooler:

1. **Direct Connection (Port 5432):** مناسب للأدوات والعمليات التي تحتاج اتصالاً مباشراً، مثل بعض مهام Alembic، وفق إعدادات الشبكة والمنصة.
2. **Transaction Pooler (Port 6543):** يعيد استخدام الاتصالات عبر PgBouncer، ويمكن أن يناسب أحمال التطبيق كثيرة الاتصالات. راجع متطلبات نمط pooling ومزود قاعدة البيانات قبل استخدامه مع ORM.

```env
# مثال توضيحي؛ خزّن كلمة المرور في متغير سري بمنصة النشر
DATABASE_URL="postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require"
```

### 3. إعداد الحاويات والنشر على Railway عبر Dockerfile

لإنشاء بيئة تشغيل قابلة للتكرار، ثبّت الاعتماديات وشغّل خادم إنتاج. طابق إصدار Python وأمر التشغيل مع المشروع والمنصة:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### خطوات النشر على Railway:

1. اربط مستودع GitHub بخدمة Railway وحدد Dockerfile أو إعدادات البناء المناسبة.
2. أضف متغيرات البيئة مثل `DATABASE_URL` و`JWT_SECRET_KEY` و`OPENAI_API_KEY` في إعدادات الخدمة السرية.
3. أنشئ نطاقاً عاماً، وتحقق من HTTPS وCORS وفحوصات الصحة وسجلات بدء التشغيل.
4. شغّل migrations بطريقة مضبوطة قبل تحويل الزيارات إلى الإصدار الجديد.

### 4. نشر Frontend على Vercel والمراقبة في الإنتاج (Observability)

بعد نشر API، اضبط عنوانها في إعدادات مشروع Vercel. يستخدم هذا المشروع Vite، لذلك يكون اسم المتغير `VITE_API_URL`:

```env
VITE_API_URL="https://kodraq-api.up.railway.app"
```

#### المراقبة وتتبع الأخطاء (Observability & Logging)

اربط الخدمة بأداة مثل **Sentry** لرصد الاستثناءات وتتبع الأداء. اضبط معدلات أخذ العينات وفق حجم الإنتاج والميزانية، ولا تسجل كلمات المرور أو tokens أو بيانات شخصية غير لازمة:

```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/project-id",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)
```

### الكبسولة المعمارية النهائية للمنهج:

1. **افصل المكونات:** اجعل الواجهة والخلفية وقاعدة البيانات مكونات مستقلة بإعدادات اتصال وصلاحيات واضحة.
2. **استخدم Connection Pooling عند الحاجة:** اضبط PgBouncer أو Transaction Pooler وفق نمط اتصالات التطبيق وحدود قاعدة البيانات.
3. **راقب باستمرار:** استخدم Health Checks والسجلات وأدوات مثل Sentry لاكتشاف الأخطاء مبكراً، واختبر خطة rollback قبل الاعتماد عليها.
""",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/7X8mJ59uW08",
            },
        ],
    },
]


def validate_curriculum_data() -> None:
    if TRACK_DATA["slug"] != "backend-ai-engineering" or TRACK_DATA["price"] != 5600.00:
        raise ValueError("Backend & AI track identity or pricing is invalid.")
    if len(MODULES_DATA) != 4:
        raise ValueError("Backend & AI curriculum must contain exactly four modules.")

    expected_orders = [1, 2, 3, 4]
    if [module["ordering"] for module in MODULES_DATA] != expected_orders:
        raise ValueError("Modules must be ordered from 1 through 4.")

    for module in MODULES_DATA:
        if not module["lessons"]:
            raise ValueError(f"Module {module['title']} must contain lessons.")
        for lesson_order, lesson in enumerate(module["lessons"], start=1):
            required_fields = {"title", "description", "content", "ordering", "video_url"}
            if required_fields - lesson.keys():
                raise ValueError(f"Lesson {lesson.get('title')} is missing required fields.")
            if lesson["ordering"] != lesson_order:
                raise ValueError(f"Lesson ordering is invalid in {module['title']}.")
            if not lesson["description"].strip() or not re.search(r"[\u0600-\u06ff]", lesson["description"]):
                raise ValueError(f"Lesson {lesson['title']} needs an Arabic description.")
            if not lesson["content"].strip() or not re.search(r"[\u0600-\u06ff]", lesson["content"]):
                raise ValueError(f"Lesson {lesson['title']} needs Arabic content.")
            if not YOUTUBE_EMBED_PATTERN.fullmatch(lesson["video_url"]):
                raise ValueError(f"Lesson {lesson['title']} needs a YouTube embed URL.")


def reset_and_seed() -> None:
    from app.models.track import Lesson, Track, TrackModule

    validate_curriculum_data()
    try:
        print("🌱 Updating Backend & AI Engineering curriculum without deleting accounts or enrollments...")
        with SessionLocal.begin() as db:
            track = db.scalar(
                select(Track).where(Track.slug == TRACK_DATA["slug"])
            )
            if track is None:
                track = Track(**TRACK_DATA)
                db.add(track)
                db.flush()
            else:
                for field, value in TRACK_DATA.items():
                    setattr(track, field, value)

            existing_modules = db.scalars(
                select(TrackModule)
                .where(TrackModule.track_id == track.id)
                .order_by(TrackModule.ordering, TrackModule.id)
            ).all()
            modules_by_order = {}
            for existing_module in existing_modules:
                modules_by_order.setdefault(existing_module.ordering, existing_module)

            seeded_lessons = []

            for module_data in MODULES_DATA:
                module = modules_by_order.get(module_data["ordering"])
                if module is None:
                    module = TrackModule(track_id=track.id)
                    db.add(module)
                module.title = module_data["title"]
                module.description = module_data["description"]
                module.ordering = module_data["ordering"]
                module.is_active = True
                db.flush()

                existing_lessons = db.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == module.id)
                    .order_by(Lesson.ordering, Lesson.id)
                ).all()
                lessons_by_order = {}
                for existing_lesson in existing_lessons:
                    lessons_by_order.setdefault(existing_lesson.ordering, existing_lesson)

                for lesson_data in module_data["lessons"]:
                    lesson = lessons_by_order.get(lesson_data["ordering"])
                    if lesson is None:
                        lesson = Lesson(module_id=module.id)
                        db.add(lesson)
                    for field, value in lesson_data.items():
                        setattr(lesson, field, value)
                    seeded_lessons.append(lesson)

            db.flush()
            expected_lesson_count = sum(len(module["lessons"]) for module in MODULES_DATA)
            if len(seeded_lessons) != expected_lesson_count:
                raise RuntimeError("The seeded lesson count does not match the curriculum.")
            for lesson in seeded_lessons:
                if (
                    not lesson.description
                    or not lesson.description.strip()
                    or not lesson.content
                    or not lesson.content.strip()
                    or not lesson.video_url
                    or not YOUTUBE_EMBED_PATTERN.fullmatch(lesson.video_url)
                ):
                    raise RuntimeError(
                        f"Lesson {lesson.title!r} is missing required curriculum details."
                    )

        print("🚀 Curriculum update completed; users, enrollments, and related records were preserved.")
    except Exception as error:
        print(f"❌ Error during reset and seed: {error}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    reset_and_seed()