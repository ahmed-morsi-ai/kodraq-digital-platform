# Module 02 — Clean Code & SOLID / كود واضح وتصميم قابل للتغيير

## Learning outcomes / مخرجات التعلّم

ستراجع كوداً من منظور قارئ جديد، تحدد أسباب التغيير، وتفصل منطق المجال عن الاعتمادات الخارجية. ستستخدم SOLID كأدوات تفكير، لا كقواعد لإنتاج class لكل سطر. النجاح يُقاس بوضوح السلوك وسهولة اختباره وتغييره مع الحفاظ على العقود.

## 1. الوضوح قبل الزخرفة / Readability

سمِّ الوظيفة حسب هدفها: `approve_submission` أو `calculate_eligibility` أو `load_curriculum`. الاسم `process_data` يترك القارئ يتخيل ما الذي يحدث. اجعل المدخلات والمخرجات ظاهرة، وقلّل state الخفية. لا تجمع تعديل قاعدة البيانات، إرسال رسالة، وتحويل HTTP response في دالة ضخمة دون حدود واضحة.

Write comments to explain a constraint or decision, not to repeat the next line. A comment saying “increment counter” adds little beside `count += 1`. A note explaining why an external call happens before acquiring a database lock can preserve an important design decision.

التكرار ليس دائماً دليلاً على ضرورة التجريد. تشابه سطرين لا يعني تطابق القاعدتين في المجال. استخراج abstraction قبل فهم اختلافات الاستخدام قد يربط ميزتين بلا سبب. ابدأ بأسماء وحدود واضحة ثم استخرج السلوك المستقر عندما تظهر الحاجة.

## 2. مبادئ SOLID باختصار

SOLID إطار لمناقشة الاعتمادات والمسؤوليات وقابلية الاستبدال، وليس قياساً آلياً لجودة المشروع. يربط Robert C. Martin هذه المبادئ بإدارة التغييرات وبناء وحدات أكثر قابلية للصيانة. [SOLID relevance](https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html).

| Principle | المعنى العملي في التمرين |
| --- | --- |
| Single Responsibility | اجمع ما يتغير للسبب نفسه، وافصل السياسات التي تتغير لأسباب مختلفة |
| Open/Closed | اجعل نقاط التوسع المطلوبة واضحة مع تقليل تعديل السلوك المستقر |
| Liskov Substitution | الاستبدال يجب أن يحافظ على العقد والسلوك المتوقع، لا على الاسم فقط |
| Interface Segregation | لا تُجبر العميل على اعتماد وظائف لا يستخدمها |
| Dependency Inversion | سياسة المجال تعتمد على عقد مناسب، والتفاصيل التقنية تحقق ذلك العقد |

## 3. دراسة حالة / A report export workflow

لدينا تقرير تقدّم الطالب. منطق اختيار البيانات يختلف عن سياسة حساب التقدّم، ويختلفان عن تنسيق CSV أو تخزين الملف. لا تجعل تغيير عنوان عمود يغيّر حساب أهلية الطالب. ارسم الحدود أولاً ثم اكتب اختباراً لكل قرار مهم.

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ProgressReport:
    student_id: int
    completed: int
    total: int

class ReportWriter(Protocol):
    def write(self, report: ProgressReport) -> str: ...

def export_report(report: ProgressReport, writer: ReportWriter) -> str:
    if report.total < 0 or not 0 <= report.completed <= report.total:
        raise ValueError("Invalid progress counts")
    return writer.write(report)

class CsvTextWriter:
    def write(self, report: ProgressReport) -> str:
        return (
            "student_id,completed,total\n"
            f"{report.student_id},{report.completed},{report.total}\n"
        )

assert export_report(ProgressReport(7, 2, 3), CsvTextWriter()).endswith("7,2,3\n")
```

المثال يُرجع نصاً فقط؛ ليس خدمة تخزين كاملة. عند إضافة storage adapter حقيقي، اجعل عقد الفشل والنجاح صريحاً. هل يعيد URL أم object key؟ هل يمكن إعادة المحاولة؟ هل الملف خاص أم عام؟ abstraction ضعيف قد يخفي اختلافاً مهماً بدلاً من معالجته.

## 4. الاستبدال والعقود / Behavioral compatibility

إذا كان القارئ يتوقع أن `get(id)` يرمي `NotFound` عند الغياب، فلا تجعل implementation آخر يُرجع كائناً فارغاً ويستمر الحساب. اكتب contract tests مشتركة للنتيجة الصحيحة، السجل المفقود، والفشل المتوقع. لا يكفي أن الدالتين تقبلان نفس المعاملات.

قارن واجهة `FileReader.read` الصغيرة مع واجهة ضخمة تلزم قارئاً read-only بدوال delete وupload وadmin_report. صمّم الواجهة من احتياج المستهلك. استخدم composition عندما تحتاج تركيب قدرات مستقلة؛ لا تبدأ بشجرة وراثة طويلة لتوفير بضعة أسطر.

## 5. Refactoring بأمان

ابدأ باختبار يثبت السلوك الحالي المهم. نفّذ خطوة صغيرة، ثم شغّل الاختبار المناسب. تغيير البنية الداخلية لا يبرر تغيير HTTP contract أو قواعد التفويض. إذا كان السلوك الحالي نفسه خاطئاً، افصل إصلاحه في وصف واضح: trigger، السلوك السابق، والسلوك الجديد.

Avoid tests that merely duplicate the implementation. Assert business outcomes and observable boundaries. A test that checks a helper was called can miss an incorrect final grade. A test that verifies one failed graduation gate blocks eligibility protects a meaningful contract.

قيّم حذف الكود بأدلة: ابحث عن المراجع والاستيرادات والمسارات النشطة، ثم احذف ما ثبت أنه غير مستخدم. لا تحذف migration قديمة لأن الكود لم يعد يستوردها؛ قاعدة بيانات قائمة قد تحتاج سلسلة التاريخ. بيانات production ليست «dead code».

## Lab / تطبيق عملي

ابدأ بدالة افتراضية تجمع قراءة الدرجات والحساب وتوليد CSV. أعد تصميمها إلى سياسة حساب، مصدر بيانات، ومخرج تقرير. أضف مخرج JSON صغيراً واختبر أن قواعد الحساب لم تتغير. سلّم before/after قصيراً يشرح كل فصل؛ لا تسلّم عشرات interfaces بلا مستهلكين.

Acceptance criteria: identical report values before and after refactoring, invalid counts rejected, missing student handled explicitly, CSV/JSON outputs covered, and no test contacts a real email or payment service.

## مراجعة ذاتية / Questions and answer notes

- هل SRP يعني دالة واحدة لكل class؟ لا؛ المعيار ترابط المسؤولية وسبب التغيير.
- هل OCP يمنع تعديل الكود القديم مطلقاً؟ لا؛ هو توجيه لتصميم نقاط التوسع ذات القيمة.
- كيف نكتشف كسر الاستبدال؟ باختبارات للعقد، تشمل الأخطاء، لا بتوقيع الدالة فقط.
- هل mock كثير دليل على تصميم جيد؟ ليس بالضرورة؛ قد يشير إلى اعتماد مفرط على تفاصيل داخلية.
- When should duplication remain? When similar code represents different policies whose evolution is not yet understood.
