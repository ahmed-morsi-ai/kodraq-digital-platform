# Module 00 — Backend Mindset / التفكير الهندسي لمطوّر Backend

## Learning outcomes / مخرجات التعلّم

بعد هذه الوحدة تستطيع تحويل مطلب غامض إلى قواعد قابلة للاختبار، تتبّع رحلة الطلب، وتحديد مسؤوليات التطبيق وقاعدة البيانات. ستكتب قراراً هندسياً يوازن الصحة والأمان والأداء والتكلفة. The goal is to explain system behavior under both normal operation and failure, not merely produce an endpoint that works once.

## 1. ابدأ من المشكلة والعقد / Problem and contract

طلب «اسمح للطالب بتسليم الواجب» ليس مواصفة مكتملة. اسأل: من هو الطالب؟ هل مسجّل في المسار؟ هل الواجب نشط؟ هل يمكن تعديل تسليم تحت المراجعة؟ ماذا يحدث عند ضغط الزر مرتين؟ حوّل الإجابات إلى قواعد واضحة قبل تصميم الجداول أو اختيار مكتبة.

An API contract describes inputs, outputs, identities, allowed state transitions, and failure behavior. An invariant must remain true after every accepted operation. Example: a student cannot alter another student's submission. This invariant belongs on the server even when the browser hides an Edit button.

اكتب أمثلة صغيرة: «طالب مسجّل يرفع مسودة» ينجح، «طالب آخر يحدّث المسودة» يُرفض، «طلبان متزامنان لإنشاء نفس السجل» لا ينتجان نسختين. هذه الأمثلة تصبح اختبارات قبول، وليست تفاصيل UI.

## 2. رحلة الطلب / Request lifecycle

مسار نموذجي: browser → reverse proxy → route → schema validation → authorization → application service → database transaction → response. Authentication answers “Who is this?” Authorization answers “May this identity perform this operation on this resource?” Validation checks whether the submitted representation meets the input contract.

افصل خطأ الوصول إلى المسار عن خطأ قاعدة البيانات. إذا كان `/api/v1/users/me` يعيد 404، افحص عنوان الخادم وOpenAPI والطريقة HTTP قبل تغيير كلمة المرور. إذا وصل الطلب وأعاد 401، فالمسار موجود لكن الهوية غير مثبتة. لا تعتبر كل فشل مشكلة CORS؛ افحص Network tab والرد الفعلي.

في طبقة الخدمة استخدم أسماء مرتبطة بالهدف مثل `submit_assignment` بدلاً من إخفاء قواعد المجال داخل دالة عامة اسمها `save`. اترك تحويل أخطاء المجال إلى HTTP في الحدود المناسبة للتطبيق. لا يحتاج محرك حساب أهلية التخرج إلى معرفة React أو تفاصيل الأزرار.

## 3. ملكية البيانات / Data ownership

كل سجل يحتاج مالكاً وسياقاً واضحاً. Submission يرتبط بطالب وAssignment، والواجب يرتبط بمسار. لا تثق في `student_id` القادم من المتصفح لتحديد صاحب الطلب؛ استخرجه من الهوية الموثقة. طابق المرجع مع السياق المسموح قبل القراءة والكتابة، ولا تكتفِ بأن السجل موجود.

Use foreign keys for valid references, unique constraints for identities that must not duplicate, and checks for simple bounds. Application validation gives useful messages; database constraints protect concurrent writes and other database clients. Neither layer replaces the other.

مثال: فحص «هل البريد موجود؟» ثم INSERT يمكن أن يتسابق مع طلب آخر. اجعل التفرد قيداً في قاعدة البيانات، ثم تعامل مع التعارض في التطبيق. لا تحل السباق بوضع تأخير زمني أو تعطيل الزر فقط.

## 4. المعاملة وحدود الفشل / Transaction boundaries

في عملية تسجيل تسليم مع ملفات، فكّر في وحدة العمل: لا نريد سجلاً يدّعي وجود ملفات لم تُحفظ. داخل PostgreSQL تجمع المعاملة تغييرات مترابطة وتتيح التراجع عنها عند الفشل. لكن كتابة ملف في تخزين خارجي لا تصبح تلقائياً جزءاً من معاملة SQL؛ تحتاج ترتيباً واضحاً وتعويضاً عند الفشل. [PostgreSQL transactions](https://www.postgresql.org/docs/16/tutorial-transactions.html).

صمّم إعادة المحاولة: إذا انقطع الاتصال بعد الحفظ وقبل وصول الرد، هل تكرار الطلب آمن؟ استخدم هوية عملية أو مفتاح idempotency عندما يتطلب المجال ذلك. نجاح HTTP المفقود لا يثبت أن الكتابة لم تحدث. اقرأ الحالة الموثوقة قبل تكرار عملية قد تؤدي إلى خصم أو إنشاء مكرر.

## 5. الأداء وقابلية الملاحظة / Performance and observability

Measure before optimizing. Separate database time, external-call time, serialization time, and queue waiting. A fast function can still sit behind a slow query. Record a request ID, route, duration, status, and safe error category; avoid logging passwords, tokens, or full private documents.

راقب عدد استعلامات القائمة، وليس زمن استعلام واحد فقط. تحميل علاقة لكل عنصر قد ينتج N+1 queries. ضع حدوداً لحجم الصفحة والملفات والمهلة. ابدأ بحل بسيط قابل للقياس؛ لا تُدخل microservices أو cache لأن الاسم يبدو متقدماً. عند إضافة cache اشرح صلاحية البيانات ومتى تُبطل النسخة المخزنة.

## Lab / تطبيق عملي

صمّم خدمة «حجز مقعد في دورة» بدون واجهة رسومية. السعة 20 مقعداً، ولا يمكن لنفس الطالب التسجيل مرتين. التسليم المطلوب: جدول بيانات، عقد HTTP مقترح، pseudocode للمعاملة، واختبارات للسعة والتكرار والتزامن. لا ترسل بريداً حقيقياً؛ سجّل حدثاً تعليمياً في الذاكرة أو استخدم test double داخل الاختبار.

Acceptance criteria:

1. Explain the owner and scope of every identifier.
2. Show one successful booking and two concurrent requests for the last seat.
3. Demonstrate that a failed operation does not consume capacity.
4. Explain the retry behavior when a response is lost.
5. Provide actual test output and a short tradeoff note.

## مراجعة ذاتية / Questions and answer notes

- لماذا لا تكفي صلاحيات UI؟ لأن العميل قابل للتعديل والطلبات يمكن إرسالها مباشرة؛ القرار النهائي للخادم.
- هل كل خطأ يستحق retry؟ لا؛ خطأ إدخال ثابت لن يصلحه التكرار، وبعض الكتابات قد تتكرر آثارها.
- هل transaction تحمي خدمة خارجية تلقائياً؟ لا؛ حدود الموارد مختلفة ويجب تصميم التعويض أو تسليم الأحداث.
- متى تختار abstraction؟ عندما توضّح مسؤولية أو تفصل اعتماداً متغيراً، لا لمجرد زيادة عدد الملفات.
- What is evidence of correctness? Repeatable tests of contracts, constraints, and failure cases, with explicit limits on what was tested.
