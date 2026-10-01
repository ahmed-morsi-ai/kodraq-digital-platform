# Module 01 — Advanced Python / بايثون المتقدمة للـ Backend

## Learning outcomes / مخرجات التعلّم

ستفهم الفرق بين الأسماء والكائنات، تبني interfaces صغيرة، وتستخدم generators وcontext managers وasyncio بوعي. ستفصل الأخطاء المتوقعة عن الأعطال، وتكتب اختبارات تكشف مشاركة الحالة وتسرب الموارد. Examples target Python 3.12 and use the standard library.

## 1. الأسماء والتغيّر / Names, aliasing, and mutability

الإسناد لا ينسخ قائمة تلقائياً. إذا كتبنا `second = first` فغالباً نتعامل مع نفس الكائن. تعديل القائمة عبر أحد الاسمين يظهر عبر الآخر. ميّز بين rebinding للاسم وتعديل الكائن نفسه. احتفظ بحالة كل طالب داخل instance مستقل؛ لا تضع قائمة التسليمات المتغيرة كخاصية class مشتركة. [Python classes and objects](https://docs.python.org/3.12/tutorial/classes.html).

```python
def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    result = [] if tags is None else list(tags)
    result.append(tag)
    return result

first = add_tag("python")
second = add_tag("sql")
assert first == ["python"]
assert second == ["sql"]
```

القرار هنا متعمد: الدالة تُرجع نسخة ولا تغيّر قائمة المستدعي. اكتب هذا العقد في الاختبار. لا تستخدم `tags=[]` كقيمة افتراضية متغيرة؛ ذلك قد يشارك الحالة بين الاستدعاءات. shallow copy لا ينسخ الكائنات الداخلية المتداخلة؛ اختبر المستوى الذي يهمك.

## 2. Type hints وعقود الوظائف

Annotations تساعد القارئ وأداة الفحص الثابت، لكنها لا تتحقق تلقائياً من JSON أثناء التشغيل. استخدم validation عند حدود النظام، ثم مرّر أنواعاً واضحة إلى الداخل. تجنّب تحويل كل شيء إلى `Any` لإسكات الأخطاء. `Protocol` يصف السلوك المطلوب دون إجبار كل implementation على وراثة class بعينه. [Python typing](https://docs.python.org/3.12/library/typing.html).

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class StudentSummary:
    student_id: int
    completed_lessons: int

class SummaryReader(Protocol):
    def get(self, student_id: int) -> StudentSummary: ...

def completed_count(reader: SummaryReader, student_id: int) -> int:
    return reader.get(student_id).completed_lessons
```

الدالة تعتمد على القدرة على القراءة فقط؛ لا تحتاج معرفة SQLAlchemy أو HTTP. `frozen=True` يمنع الإسناد المعتاد إلى حقول dataclass، لكنه ليس تجميداً عميقاً لأي قائمة داخلية. اختر حقولاً immutable عندما يتطلب العقد قيمة ثابتة.

## 3. Iterators وgenerators

Generator يسلّم العناصر تدريجياً بدلاً من بناء قائمة كاملة مسبقاً. هذا مفيد لمعالجة ملفات كبيرة، لكنه لا يضمن أن بقية الخطوات لا تحتفظ بالبيانات كلها. إذا حولت الناتج إلى `list` فأنت أعدت materialization. انتبه أيضاً إلى أن generator المعتاد يُستهلك مرة واحدة وأن الاستثناء قد يظهر أثناء iteration، لا عند إنشائه.

```python
from collections.abc import Iterator
from pathlib import Path

def nonblank_lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield line.rstrip("\n")
```

هذا مثال لترشيح الأسطر، وليس قاعدة عامة لتنظيف كود المصدر: حذف المسافات أو الأسطر قد يغيّر معنى المادة التي تُدخلها إلى RAG. صمّم normalization صريحاً وثابتاً، ثم اختبر أن النص الناتج لا يفقد indentation مهمة.

## 4. إدارة الموارد والأخطاء / Resource lifetime

استخدم `with` لتحديد عمر الملف أو المعاملة. في context manager مخصص، ضع التنظيف في `finally` كي يحدث عند الخروج الطبيعي أو عند الاستثناء. لا تبتلع الخطأ الأصلي وتُرجع نجاحاً وهمياً. [contextlib](https://docs.python.org/3.12/library/contextlib.html).

ميّز `ValueError` للإدخال غير المقبول عن فشل اتصال يحتاج معالجة مختلفة. التقط الاستثناء عند الطبقة القادرة على اتخاذ قرار؛ لا تضع `except Exception: pass` حول كل عملية. عند إعادة صياغة الخطأ، احتفظ بالسياق الداخلي عند الحاجة، مع رسالة آمنة للمستخدم لا تكشف كلمة مرور أو connection string.

## 5. التزامن / asyncio, cancellation, and blocking

`async def` لا يجعل كل ما بداخله غير حاجب. استدعاء مكتبة I/O متزامنة داخل coroutine قد يوقف event loop. استخدم عميل async مناسباً أو افصل العمل الحاجب عند الحاجة. اجعل المهلة والإلغاء جزءاً من العقد. `TaskGroup` ينظم مجموعة مهام مرتبطة ويُظهر فشلها بطريقة منظمة؛ راجع سلوك الاستثناءات والإلغاء قبل استخدامه. [asyncio tasks](https://docs.python.org/3.12/library/asyncio-task.html).

```python
import asyncio

async def read_label(number: int) -> str:
    await asyncio.sleep(0.01)
    return f"lesson-{number}"

async def labels() -> list[str]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(read_label(i)) for i in range(3)]
    return [task.result() for task in tasks]

assert asyncio.run(labels()) == ["lesson-0", "lesson-1", "lesson-2"]
```

التزامن هنا يغيّر طريقة انتظار المهام، ولا يضمن تسريع عمل حسابي ثقيل. لا تشارك Session واحدة بين مهام متزامنة؛ صمّم ملكية الموارد وفق مكتبة الاتصال المستخدمة. ابدأ بقياس واضح قبل إضافة concurrency.

## Lab / تطبيق عملي

ابنِ parser لملف درجات UTF-8. تجاهل الأسطر الفارغة وفق عقد معلن، ارفض الدرجات خارج 0–100، وأعد تقريراً بالأخطاء مع أرقام الأسطر. افصل القراءة عن parsing وعن حساب المتوسط. لا تُرجع صفراً للملف التالف وكأنه طالب درجته صفر.

Acceptance criteria: tests for empty input, Arabic names, invalid numbers, resource cleanup after an exception, and two independent runs without shared mutable state. Add a large synthetic input test and explain what is streamed and what remains in memory.

## مراجعة ذاتية / Questions and answer notes

- هل type hints بديل عن Pydantic عند حدود API؟ لا؛ الفحص الثابت والتحقق وقت التشغيل مسؤوليتان مختلفتان.
- هل النسخ السطحي يعزل القوائم المتداخلة؟ لا؛ تبقى مراجع داخلية مشتركة.
- لماذا نختبر استدعاءين متتابعين؟ لاكتشاف تسرب الحالة بين الطلبات.
- هل async يساوي parallel CPU execution؟ لا؛ حدّد نوع العمل وموارد التنفيذ أولاً.
- What should an error report preserve? A useful category and location, without hiding failure or exposing secrets.
