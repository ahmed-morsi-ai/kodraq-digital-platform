from __future__ import annotations
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
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
                "video_url": "https://www.youtube.com/embed/7t2alSnE2rI",
            },
            {
                "title": "التحقق من البيانات باستخدام Pydantic V2",
                "description": "افهم نماذج Pydantic V2 وحقولها المقيدة وعمليات serialization والتحقق المخصص لبناء حدود آمنة بين API وبيانات التطبيق.",
                "content": """
### 1. ثورة Pydantic V2: لماذا تمت إعادة كتابته بلغة Rust؟

في الإصدار الثاني (V2)، انتقل **Pydantic** من كونه مجرد مكتبة جيدة للتحقق من البيانات إلى "وحش أداء" حقيقي. تم استبدال المحرك الداخلي (Core) بمحرك مكتوب بلغة **Rust** (`pydantic-core`)، مما أدى إلى زيادة سرعة التحقق من البيانات (Validation) بمقدار **5 إلى 50 ضعفاً** مقارنة بـ V1.

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

ماذا لو أردنا التحقق من منطق معقد لا يمكن لـ `Field` تغطيته؟ هنا نستخدم `@field_validator` (للتحقق من حقل واحد) و `@model_validator` (للتحقق من عدة حقول معاً).

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
                "video_url": "https://www.youtube.com/embed/Vj-iU-8_xLs",
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
                "description": "تعلّم تحويل متطلبات المنتج إلى مخطط PostgreSQL سليم باستخدام التطبيع والمفاتيح والعلاقات والقيود والفهارس المناسبة.",
                "content": "تبدأ الوحدة بتحديد الكيانات وخصائصها ثم تصميم الجداول والمفاتيح الأساسية والخارجية. ستدرس التطبيع لتقليل التكرار، وتمثيل علاقات one-to-many وmany-to-many، واستخدام UNIQUE وCHECK وNOT NULL لحماية قواعد المجال. كما ستراجع المعاملات والعزل والفهارس، وتقرأ أمثلة على JOIN وGROUP BY، ثم تستخدم EXPLAIN لفهم خطط الاستعلام وتختار الفهارس بناء على أنماط القراءة والكتابة الفعلية.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/26ls5lNiijk",
            },
            {
                "title": "نماذج SQLAlchemy وإدارة الجلسات",
                "description": "استخدم SQLAlchemy ORM والعلاقات وواجهة select في الإصدار 2.x مع ضبط عمر Session وحدود المعاملات وتجنب استعلامات N+1.",
                "content": "ستعرّف نماذج ORM مرتبطة بجداول PostgreSQL، وتنفذ القراءة والإنشاء والتحديث باستخدام select وSession. تشرح المادة العلاقات بين Track وModule وLesson واستراتيجيات lazy loading وselectinload وjoinedload، وأثر كل منها على عدد الاستعلامات. ستتعلم إدارة commit وrollback عند حدود العملية، وعدم مشاركة Session بين مهام متزامنة، وكيفية فحص SQL الناتج واختبار سلامة البيانات عند حدوث استثناء.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/529LYDgRTgQ",
            },
            {
                "title": "ترحيل المخطط باستخدام Alembic وSQLAlchemy",
                "description": "أنشئ migrations قابلة للمراجعة والتكرار، وطبّق تغييرات المخطط والبيانات بأمان عبر بيئات التطوير والاختبار والإنتاج.",
                "content": "تشرح الوحدة إعداد Alembic وربطه بmetadata الخاصة بـSQLAlchemy، وإنشاء revision ومراجعة أوامر upgrade وdowngrade قبل تشغيلها. ستتدرب على إضافة عمود أو فهرس وتعديل قيود، وعلى كتابة data migration منفصلة عند الحاجة. كما ستتعلم ترتيب revisions، والتعامل مع قاعدة بيانات قائمة، وتخطيط تغييرات متوافقة أثناء النشر بحيث لا يعتمد الإصدار الجديد على مخطط لم يصل بعد إلى جميع البيئات.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/e8NnDz8uT7o",
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
                "description": "تعلّم كتابة تعليمات واضحة للنماذج اللغوية تحدد الدور والهدف والسياق والقيود وشكل المخرجات، مع تقييم الجودة وتقليل الإجابات غير المدعومة.",
                "content": "تشرح المادة كيف تعالج نماذج اللغة النصوص وما الذي تعنيه الرموز والسياق وحدود طول prompt. ستبني تعليمات تتضمن دوراً ومهمة وسياقاً وأمثلة وقيوداً صريحة، وتفصل مدخلات المستخدم عن تعليمات النظام. كما ستتعلم طلب مخرجات منظمة، واختبار prompt على حالات متنوعة، ورصد الهلوسة والتحيز، وعدم اعتبار صياغة prompt بديلاً عن التفويض والتحقق من البيانات في التطبيق.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/jC4v5AS4RIM",
            },
            {
                "title": "Embeddings والبحث المتجهي باستخدام pgvector",
                "description": "افهم تحويل النص إلى embeddings وتخزينها في PostgreSQL عبر pgvector، ثم استرجاع المقاطع باستخدام مقاييس التشابه والفهارس المتجهية.",
                "content": "ستقسم المستندات إلى chunks مناسبة، وتنشئ embedding لكل مقطع وتحفظ المتجه مع النص ومعرّف المصدر والبيانات الوصفية. تشرح الوحدة نوع vector في pgvector ومقاييس المسافة الشائعة، وكيفية تنفيذ nearest-neighbor search وإضافة فهارس مثل HNSW عند ملاءمتها. ستوازن بين حجم المقطع والدقة والتكلفة، وتضيف شروط تصفية بحسب track أو lesson قبل إرجاع النتائج لمنع تسرب بيانات غير مصرح بها.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/klTvEwg3oJ4",
            },
            {
                "title": "تصميم وتنفيذ بنية RAG متكاملة",
                "description": "اربط ingestion والتقسيم وembeddings والاسترجاع وتوليد الإجابة في خط RAG يعرض الأدلة ويتعامل بوضوح مع نقص السياق.",
                "content": "تتبع الوحدة خط المعالجة من إدخال المستندات وتنظيفها وتقسيمها إلى chunks، ثم إنشاء embeddings وفهرستها واسترجاع أكثر المقاطع صلة بالسؤال. ستبني prompt يحيط السياق المسترجع بحدود واضحة، وتضيف مصادر الإجابة، وتعيد رداً صريحاً عند غياب أدلة كافية. كما ستدرس عزل المستأجرين والصلاحيات، وحدود السياق، والمهلات والأخطاء، وقياس جودة الاسترجاع والدقة وزمن الاستجابة واستهلاك الرموز.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/T-D1OfcDW1M",
            },
        ],
    },
    {
        "title": "Module 4: النشر السحابي والتشغيل الإنتاجي - Module 04",
        "description": "جهّز تطبيق الباك إند للعمل الإنتاجي عبر إعداد الخادم وGunicorn/Uvicorn، ثم أتمتة الفحوصات والبناء والنشر إلى Vercel وRailway.",
        "ordering": 4,
        "lessons": [
            {
                "title": "إعداد خدمة الباك إند للإنتاج",
                "description": "جهّز تطبيق FastAPI للإنتاج بإعدادات منفصلة وآمنة، وملفات تشغيل وحاويات قابلة للتكرار وفحوصات صحة ومراقبة أساسية.",
                "content": "تشرح الوحدة نقل الإعدادات إلى environment variables وإدارة الأسرار خارج المستودع، وبناء صورة Docker وتشغيل التطبيق بمستخدم محدود الصلاحيات. ستضيف health وreadiness checks، وتضبط logging دون تسجيل tokens أو بيانات حساسة، وتفصل إعدادات التطوير عن الإنتاج. كما ستراجع متطلبات PostgreSQL والتخزين الدائم والنسخ الاحتياطي ومراجعة migrations قبل إتاحة الإصدار للمستخدمين.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/3c-iBn73dDE",
            },
            {
                "title": "تشغيل FastAPI باستخدام Gunicorn وUvicorn",
                "description": "افهم دور Uvicorn كخادم ASGI ودور Gunicorn في إدارة workers، واضبط عدد العمليات والمهلات والإغلاق الملائم لحمل التطبيق.",
                "content": "توضح المادة الفرق بين ASGI server وprocess manager، وكيف يشغّل Gunicorn workers من Uvicorn لتطبيق FastAPI. ستختار إعدادات workers والمهلات وفق موارد المنصة ونوع I/O، وتتعامل مع graceful shutdown وإعادة تشغيل العمال، وتفحص سجلات بدء التشغيل وأخطاء health checks. كما ستتعرف على أثر عدد العمليات على اتصالات قاعدة البيانات والذاكرة، ولماذا يجب اختبار إعداد التشغيل الفعلي بدلاً من استخدام خادم التطوير في الإنتاج.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/R8_veQiYBjI",
            },
            {
                "title": "CI/CD والنشر على Vercel وRailway",
                "description": "أنشئ خط CI/CD يشغّل الاختبارات ويبني الواجهة والخادم، ثم ينشرهما على Vercel وRailway مع إعداد الأسرار والنطاقات وقاعدة البيانات.",
                "content": "سترتب مراحل CI للتحقق من التنسيق والأنواع والاختبارات وبناء artifacts قبل الدمج، ثم تهيئ CD لنشر الواجهة على Vercel وخدمة FastAPI وقاعدة البيانات على Railway. تشرح الوحدة ضبط متغيرات البيئة والنطاقات وCORS، وتشغيل migrations بطريقة آمنة، ومراجعة health checks والسجلات بعد النشر. كما ستضع خطة rollback للإصدارات الفاشلة، وتتحقق من أن أسرار الإنتاج لا تظهر في ملفات البناء أو سجلات CI.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/HG6yIjZapSA",
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
    from app.models.enrollment import Enrollment
    from app.models.track import Lesson, Resource, Track, TrackModule
    from app.models.user import User

    validate_curriculum_data()
    try:
        print("🧹 Cleaning existing database and seeding Backend & AI Engineering...")
        with SessionLocal.begin() as db:
            db.query(Enrollment).delete()
            db.query(Resource).delete()
            db.query(Lesson).delete()
            db.query(TrackModule).delete()
            db.query(Track).delete()
            db.query(User).delete()

            track = Track(**TRACK_DATA)
            db.add(track)
            db.flush()

            for module_data in MODULES_DATA:
                module = TrackModule(
                    track_id=track.id,
                    title=module_data["title"],
                    description=module_data["description"],
                    ordering=module_data["ordering"],
                )
                db.add(module)
                db.flush()
                for lesson_data in module_data["lessons"]:
                    db.add(Lesson(module_id=module.id, **lesson_data))

            db.flush()
            seeded_lessons = (
                db.query(Lesson)
                .join(TrackModule, Lesson.module_id == TrackModule.id)
                .filter(TrackModule.track_id == track.id)
                .all()
            )
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

        print("🚀 Database reset completed with one track, four modules, and complete lessons.")
    except Exception as error:
        print(f"❌ Error during reset and seed: {error}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    reset_and_seed()