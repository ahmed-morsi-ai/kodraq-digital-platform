from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"\s+", " ", value.strip().casefold())
    return value


def lesson_content(
    *,
    track_name: str,
    module_title: str,
    lesson_title: str,
    focus: str,
    lab: str,
    outcome: str,
) -> str:
    return f"""## الهدف التعليمي

في هذا الدرس من مسار **{track_name}** داخل وحدة **{module_title}**، ستبني فهمًا عمليًا لـ **{focus}**، مع التركيز على كيفية تحويل المفهوم إلى قرار هندسي قابل للتنفيذ وليس مجرد معرفة نظرية.

### ماذا ستتعلم؟
- فهم المبادئ الأساسية للمفهوم وربطها بالمشكلة الهندسية الفعلية.
- معرفة المصطلحات والأنماط والأخطاء الشائعة المرتبطة بالموضوع.
- تحليل المتطلبات قبل كتابة الحل، ثم تقسيم الحل إلى خطوات صغيرة قابلة للاختبار.
- قراءة نتائج التنفيذ وتحديد سبب الخطأ بدل الاعتماد على التجربة العشوائية.

### الدرس العملي: {lesson_title}

**التطبيق المقترح:** {lab}

ابدأ بتعريف المدخلات والمخرجات والقيود. بعد ذلك نفّذ الحل على مراحل، وسجّل الفرضيات التي بنيت عليها قراراتك. عند ظهور مشكلة، استخدم سجلات التنفيذ أو أدوات القياس أو الاختبارات لتحديد السبب الجذري.

### معيار الإتقان
بنهاية الدرس يجب أن تكون قادرًا على **{outcome}**، وأن تشرح لماذا اخترت الحل الحالي وما البدائل التي رفضتها وما trade-offs الناتجة عن هذا القرار.

### مهمة قصيرة
نفّذ التطبيق بنفسك، ثم اكتب فقرة قصيرة تجيب عن الأسئلة التالية:
1. ما أهم قرار هندسي اتخذته؟
2. ما الخطأ أو السيناريو الحدي الأكثر احتمالًا؟
3. كيف ستختبر الحل قبل دمجه في مشروع أكبر؟
"""


# Each tuple is:
# (module title, module description, [(lesson title, focus, practical lab, mastery outcome), ...])
CURRICULA: dict[str, dict] = {
    "full-stack-backend-ai-engineering": {
        "aliases": [
            "Full-Stack Backend & AI Engineering",
            "هندسة الباك إند والذكاء الاصطناعي",
            "هندسة الباك اند والذكاء الاصطناعي",
        ],
        "modules": [
            ("الأسبوع 1: أساسيات Python وبيئة التطوير",
             "بناء أساس قوي في Python، إدارة البيئة، تنظيم المشروع، كتابة كود قابل للقراءة والاختبار.",
             [
                 ("منطق البرمجة وكتابة Python لأول مرة", "المتغيرات والأنواع والتعبيرات ومسار تنفيذ البرنامج", "إنشاء برنامج CLI بسيط يستقبل بيانات مستخدم ويطبق قواعد تحقق", "تفكيك مشكلة صغيرة إلى خطوات Python واضحة."),
                 ("الدوال والنطاقات والاستثناءات", "تصميم الدوال وscope ورفع ومعالجة الأخطاء", "بناء حزمة دوال للتحقق من بيانات مستخدم مع رسائل أخطاء مفيدة", "اختيار حدود الدوال ومعالجة الاستثناءات بشكل صحيح."),
                 ("القوائم والقواميس والمجموعات", "هياكل البيانات الأساسية وأنماط التعامل معها", "تحويل بيانات خام إلى تقرير باستخدام list/dict/set comprehensions", "اختيار بنية البيانات المناسبة للمهمة."),
                 ("تنظيم مشروع Python", "الحزم والوحدات وملفات الإعداد وفصل المسؤوليات", "إنشاء مشروع متعدد الوحدات مع ملف تشغيل واختبار أولي", "إنشاء هيكل مشروع يمكن توسيعه دون فوضى.")
             ]),
            ("الأسبوع 2: هندسة REST APIs باستخدام FastAPI",
             "الانتقال من سكربتات محلية إلى خدمة HTTP منظمة مع Schemas وDependency Injection وتوثيق OpenAPI.",
             [
                 ("HTTP وREST من منظور المطور", "methods وstatus codes وheaders وJSON", "تصميم عقد API لخدمة إدارة المسارات التعليمية", "تمييز الموارد والعمليات واستجابات HTTP المناسبة."),
                 ("بناء أول API بـ FastAPI", "routers وpath/query parameters وrequest bodies", "إنشاء CRUD مصغر للمقررات والطلاب", "بناء endpoint من العقد حتى الاستجابة."),
                 ("Pydantic والتحقق من البيانات", "schemas والتحقق والـserialization", "تعريف نماذج إنشاء وتحديث وعرض لكيان Track", "منع البيانات غير الصحيحة على حدود الخدمة."),
                 ("Dependency Injection والتنظيم الطبقي", "dependencies وفصل الـAPI عن الخدمات", "إضافة dependency للجلسة وقواعد صلاحيات بسيطة", "تنظيم route handler بحيث لا يتحول إلى طبقة أعمال ضخمة.")
             ]),
            ("الأسبوع 3: PostgreSQL وSQLAlchemy",
             "فهم البيانات العلائقية وربطها بـ SQLAlchemy بطريقة تدعم النمو والاختبارات.",
             [
                 ("أساسيات PostgreSQL", "الجداول والمفاتيح والقيود والفهارس", "تصميم جداول users وtracks وenrollments", "اختيار العلاقات والقيود التي تحمي البيانات."),
                 ("SQLAlchemy Models والعلاقات", "Foreign Keys وrelationships وcascade", "ربط Track بـ Module وLesson بعلاقات واضحة", "بناء model graph متماسك."),
                 ("CRUD والاستعلامات المتقدمة", "select وfilter وordering وjoins", "كتابة استعلامات لاسترجاع تقدم الطالب ومساره", "كتابة استعلامات واضحة وقابلة للصيانة."),
                 ("Alembic وإدارة تغييرات المخطط", "migrations والترقية والتراجع", "إضافة عمود وفهرس مع migration قابلة للإعادة", "إدارة schema evolution بأمان.")
             ]),
            ("الأسبوع 4: Authentication وRBAC وأمن الـAPI",
             "بناء طبقة وصول حقيقية تحمي بيانات الطلاب والإدارة والمحتوى المدفوع.",
             [
                 ("JWT وتدفق تسجيل الدخول", "access tokens وOAuth2 password flow", "ربط login بـ Bearer token ثم endpoint محمي", "شرح دورة حياة التوكن ومخاطر تخزينه."),
                 ("Users والأدوار والصلاحيات", "RBAC ومبدأ أقل صلاحية", "تطبيق فرق بين student وadmin على endpoint واحد", "فرض authorization في المكان الصحيح."),
                 ("حماية المدفوعات والـpaywall", "فصل حالة الدفع عن حالة الوصول", "تصميم قاعدة تمنع active enrollment لمسار premium دون تحقق", "تمييز payment state عن enrollment state."),
                 ("المدخلات الحساسة والرفع الآمن", "validation وحجم الملف والامتدادات", "إنشاء سياسة رفع receipt آمنة مع أسماء ملفات عشوائية", "تقليل مخاطر file upload وdata leakage.")
             ]),
            ("الأسبوع 5: Testing وQuality Engineering",
             "إنشاء طبقة جودة تمنع regressions وتدعم التطوير السريع.",
             [
                 ("Unit Tests فعالة", "اختبار functions وservices والـedge cases", "كتابة اختبارات لحساب حالة enrollment", "اختيار حدود الاختبار المناسبة."),
                 ("API Integration Testing", "TestClient وfixtures وقاعدة اختبار", "اختبار login ثم الوصول إلى track محمي", "بناء سيناريو backend متكامل."),
                 ("Ruff وType Hints وCode Quality", "linting وtyping والانضباط الأسلوبي", "إصلاح module يحتوي على أخطاء lint وtyping", "قراءة أدوات الجودة كإشارات هندسية."),
                 ("Regression Testing للمدفوعات", "صياغة حالات النجاح والفشل", "اختبار premium بدون دفع وpending وverified", "منع عودة paywall bypass بعد refactor.")
             ]),
            ("الأسبوع 6: Async وBackground Jobs وRedis",
             "فهم الأعمال غير المتزامنة وطوابير المهام والعمليات التي لا يجب أن تحجز طلب HTTP.",
             [
                 ("Async في Python وFastAPI", "event loop ومتى تستخدم async", "تحويل endpoint I/O بسيط إلى async", "معرفة متى يكون async مفيدًا ومتى لا."),
                 ("Background Tasks", "فصل المهام البطيئة عن الاستجابة", "إنشاء job لإرسال إشعار بعد تحقق الدفع", "تصميم flow لا يحبس request."),
                 ("Redis والكاش", "keys وTTL واستخدام Redis كطبقة دعم", "تخزين نتيجة query متكرر مع TTL", "اختيار مكان الكاش وتجنب البيانات القديمة."),
                 ("Queue Architecture", "retries وidempotency وdead-letter thinking", "تصميم مهمة معالجة receipt قابلة لإعادة المحاولة", "منع تكرار الأثر عند retry.")
             ]),
            ("الأسبوع 7: هندسة تطبيقات الذكاء الاصطناعي",
             "من استدعاء نموذج لغوي إلى أنظمة AI قابلة للقياس والاختبار ومعزولة عن بيانات العملاء.",
             [
                 ("LLM APIs وPrompt Contracts", "messages وtemperature وstructured output", "بناء خدمة تلخص محتوى درس إلى نقاط عملية", "تصميم prompt contract قابل للاختبار."),
                 ("Embeddings والبحث الدلالي", "vectors وchunking وsimilarity", "إنشاء pipeline نظري لمحتوى أكاديمية", "شرح لماذا وكيف نستخدم embeddings."),
                 ("RAG وعزل المعرفة", "retrieval context وتقليل hallucination", "تصميم RAG يختار مستندات لمسار واحد فقط", "ربط retrieval بالـauthorization."),
                 ("AI Safety وObservability", "PII وusage logging وcost controls", "إضافة قياس token usage وسجل قرار مبسط", "تحديد حدود تشغيل AI في منتج حقيقي.")
             ]),
            ("الأسبوع 8: Deployment وObservability وCapstone",
             "تحويل النظام إلى خدمة قابلة للنشر والمراقبة مع مشروع تخرج يجمع طبقات المسار.",
             [
                 ("Docker وConfiguration", "containers وenvironment variables", "تشغيل API وPostgreSQL في بيئة محلية متكررة", "فصل configuration عن source code."),
                 ("CI/CD وRelease Discipline", "build وtest وmigration gates", "بناء pipeline يمنع release عند فشل الاختبارات", "ربط quality gates بالنشر."),
                 ("Logging وHealth وMonitoring", "structured logs وhealth checks", "إضافة health endpoint وسجل request correlation", "تحديد الإشارات التي تحتاج مراقبة."),
                 ("مشروع التخرج: منصة أكاديمية", "دمج auth وtracks وpayments وAI", "بناء API مصغر لرحلة الطالب من التسجيل حتى التعلم", "تجميع معماري كامل مع توثيق قرارات التصميم.")
             ]),
        ],
    },
    "advanced-frontend-architecture": {
        "aliases": ["Advanced Frontend Architecture", "هندسة الواجهات الأمامية المتقدمة", "هندسة الواجهات الامامية المتقدمة"],
        "modules": [
            ("الأسبوع 1: Web Platform وHTML وCSS", "فهم المتصفح وبناء واجهات دلالية ومتجاوبة.", [
                ("بنية صفحة الويب", "HTML semantics وforms وaccessibility", "بناء صفحة تسجيل دلالية", "اختيار عناصر HTML المناسبة."),
                ("CSS Layout", "Flexbox وGrid وresponsive design", "بناء لوحة مسارات متجاوبة", "تصميم layout يعمل عبر breakpoints."),
                ("Design Tokens", "spacing وtypography وconsistency", "استخراج tokens من صفحة موجودة", "تحويل الواجهة إلى نظام قابل لإعادة الاستخدام."),
                ("Accessibility Fundamentals", "keyboard navigation وlabels وcontrast", "مراجعة نموذج تسجيل وفق checklist", "اكتشاف وإصلاح مشكلات وصول واضحة.")
            ]),
            ("الأسبوع 2: TypeScript وReact", "الانتقال إلى مكونات React قوية بعقود types واضحة.", [
                ("TypeScript للواجهات", "interfaces وunion types وgenerics", "تعريف types لمسار ومستخدم", "منع أخطاء البيانات قبل runtime."),
                ("React Components", "composition وprops وchildren", "تقسيم صفحة Track إلى components", "اختيار حدود المكونات."),
                ("Hooks بوعي معماري", "useState وuseEffect وuseMemo", "إدارة تحميل بيانات track", "تجنب effects غير الضرورية."),
                ("Rendering Patterns", "conditional rendering وkeys وlists", "بناء قائمة lessons", "إدارة الحالات الفارغة والتحميل.")
            ]),
            ("الأسبوع 3: State Architecture", "فصل local UI state عن server state وبناء تدفقات قابلة للتوسع.", [
                ("State Ownership", "مكان كل state ولماذا", "إعادة تنظيم state لصفحة تعلم", "منع duplicated state."),
                ("Server State", "fetching وcache وinvalidations", "تصميم flow لتحديث enrollment", "فهم lifecycle لبيانات الخادم."),
                ("Forms وValidation", "controlled inputs وvalidation", "نموذج رفع receipt متين", "إدارة أخطاء الإدخال بوضوح."),
                ("Error Boundaries وRecovery", "fallbacks وretry UX", "إضافة retry لصفحة بيانات", "جعل failure قابلاً للتعافي.")
            ]),
            ("الأسبوع 4: API Integration وAuth UX", "ربط React بعقود API مع التعامل الصحيح مع التوكنات والحالات الانتقالية.", [
                ("Axios Service Layer", "baseURL وinterceptors", "إنشاء service لمسارات الأكاديمية", "فصل HTTP عن UI."),
                ("Auth Context", "session hydration وlogout", "بناء session bootstrap", "إدارة جلسة المستخدم بأمان."),
                ("Protected Routes", "route guards وredirects", "قفل صفحة تعلم لغير المسجل", "تطبيق authorization UX."),
                ("Payment Flow UX", "checkout وpending وsuccess", "بناء شاشة دفع متعددة الحالات", "تمثيل payment state دون التباس.")
            ]),
            ("الأسبوع 5: Design System وUX Engineering", "تحويل الواجهة إلى نظام تصميم متسق وقابل للتطوير.", [
                ("Reusable UI Components", "Button وCard وModal contracts", "بناء مجموعة primitive صغيرة", "تقليل التكرار البصري."),
                ("Dark/Light Theme", "tokens وtheme switching", "توحيد ألوان صفحات مختلفة", "منع theme drift."),
                ("Microinteractions", "loading وdisabled وfeedback", "تحسين زر CTA وupload flow", "إعطاء المستخدم feedback مناسب."),
                ("Arabic RTL UX", "direction وtypography وmixed LTR", "صفحة عربية تحتوي أرقام وروابط", "منع مشاكل RTL الشائعة.")
            ]),
            ("الأسبوع 6: Performance وTesting", "تحسين السرعة والاعتمادية والتحقق من البناء النهائي.", [
                ("Rendering Performance", "memoization وrender boundaries", "تحليل component يعاد رسمه كثيرًا", "اختيار التحسين الضروري فقط."),
                ("Code Splitting", "lazy routes وbundles", "تقسيم صفحات admin", "خفض تكلفة initial load."),
                ("Frontend Testing", "component وintegration mindset", "اختبار checkout states", "اختبار السلوك بدل التفاصيل الداخلية."),
                ("Lint وBuild Gates", "TypeScript وoxlint وVite build", "إنشاء checklist قبل release", "قراءة نتائج أدوات الجودة واتخاذ قرار.")
            ]),
            ("الأسبوع 7: Data Architecture وScalable UI", "تصميم تطبيقات كبيرة بعقود موحدة وتغذية بيانات منظمة.", [
                ("Feature-Based Structure", "تنظيم حسب المجال", "إعادة ترتيب feature tracks", "فصل domain boundaries."),
                ("Typed API Contracts", "DTOs وتناسق response types", "توحيد Track وEnrollment types", "تقليل contract drift."),
                ("Pagination وFiltering UX", "query params وempty states", "بناء قائمة قابلة للتصفية", "تصميم تجربة بحث واضحة."),
                ("Optimistic Updates", "pending UI وrollback", "تحديث progress مع fallback", "معرفة متى لا ينبغي استخدام optimistic UI.")
            ]),
            ("الأسبوع 8: Production Frontend Capstone", "دمج النظام في واجهة إنتاجية كاملة من التسويق حتى التعلم.", [
                ("Sales Page Architecture", "hero وbenefits وCTA", "تحويل TrackDetail إلى sales page", "إقناع المستخدم قبل enrollment دون كشف المحتوى."),
                ("Learning Experience", "modules وlessons وprogress", "بناء شاشة curriculum متدرجة", "إظهار الوصول حسب الحالة."),
                ("Admin Experience", "tables وfilters وactions", "بناء شاشة payment verification", "تقليل أخطاء الإدارة."),
                ("Capstone Review", "architecture review وaccessibility وperformance", "مراجعة frontend كامل وفق release checklist", "تبرير القرارات المعمارية.")
            ]),
        ],
    },
    "mechatronics-robotics-engineering": {
        "aliases": ["Mechatronics & Robotics Engineering", "دبلومة الميكاترونكس والروبوتات", "الميكاترونكس والروبوتات"],
        "modules": [
            ("الأسبوع 1: الأساسيات الرياضية والكهربائية", "بناء أساس في الوحدات والدوائر والقوى اللازمة لفهم الأنظمة الكهروميكانيكية.", [
                ("الوحدات والقياسات الهندسية", "SI units وaccuracy وmeasurement error", "قياس جهد وتيار عدة أحمال", "قراءة القياس مع فهم الخطأ."),
                ("قوانين الدوائر الأساسية", "Ohm وKirchhoff", "تحليل دائرة مقاومات بسيطة", "حساب الجهد والتيار المتوقعين."),
                ("المحركات والحركة", "torque وspeed وpower", "اختيار محرك لتطبيق صغير", "ربط القدرة بالمواصفات."),
                ("سلامة المختبر", "grounding وcurrent limits وrisk management", "إنشاء checklist قبل تشغيل منظومة", "تطبيق السلامة قبل القياس.")
            ]),
            ("الأسبوع 2: Sensors وActuators", "فهم كيفية استشعار البيئة وتحويل القرار إلى حركة.", [
                ("قراءة الحساسات", "analog vs digital وnoise", "قراءة حساس مسافة", "تمييز الإشارة من الضوضاء."),
                ("Actuators", "DC motors وservos وsolenoids", "تشغيل محرك عبر driver", "اختيار actuator حسب الحمل."),
                ("Signal Conditioning", "filtering وscaling وcalibration", "معايرة حساس تناظري", "تحويل signal إلى قيمة هندسية."),
                ("Sensor Fusion Basics", "دمج أكثر من حساس", "دمج encoder مع limit switch", "تحسين الثقة في الحالة المقاسة.")
            ]),
            ("الأسبوع 3: Microcontrollers وC/C++", "الانتقال من النظرية إلى التحكم المباشر بالعتاد.", [
                ("معمارية المتحكم", "CPU وmemory وGPIO", "رسم خريطة peripheral بسيطة", "فهم مسار الإشارة داخل MCU."),
                ("Embedded C Basics", "types وbit operations وmemory awareness", "كتابة driver أولي لـGPIO", "التحكم في register بسيط."),
                ("Timers وPWM", "timers وduty cycle", "تغيير سرعة محرك بـPWM", "ربط duty cycle بالسلوك."),
                ("Debugging Hardware/Software", "serial logs وwatch variables", "تتبع bug في قراءة حساس", "تحديد هل المشكلة في الكود أم العتاد.")
            ]),
            ("الأسبوع 4: Control Systems وPID", "بناء حلقات تحكم مستقرة وقياس أداء النظام.", [
                ("Feedback Systems", "open loop vs closed loop", "مقارنة نظامي تحكم بسيطين", "شرح قيمة feedback."),
                ("PID Components", "P وI وD", "محاكاة PID على ورق وبيانات", "فهم أثر كل معامل."),
                ("Tuning عملي", "overshoot وsettling وstability", "تجربة tuning تدريجية", "اختيار معاملات أولية منطقية."),
                ("Control Safety", "limits وfault handling", "إيقاف المحرك عند تجاوز شرط", "إضافة safety interlocks.")
            ]),
            ("الأسبوع 5: Mechanisms وKinematics", "فهم الحركة الميكانيكية قبل ربطها بالبرمجة.", [
                ("Degrees of Freedom", "joint types وcoordinates", "تحليل ذراع آلي ثنائي المفصل", "حساب درجات الحرية."),
                ("Forward Kinematics", "تحويلات ومصفوفات", "حساب موضع end-effector", "ربط زوايا المفاصل بالموقع."),
                ("Inverse Kinematics", "تحويل الموقع إلى زوايا", "حل حالة ذراع بسيطة", "تمييز multiple solutions."),
                ("Mechanical Tolerances", "backlash وfriction وclearance", "قياس خطأ ميكانيكي", "ربط التصميم الميكانيكي بالأداء.")
            ]),
            ("الأسبوع 6: Robotics وROS2", "إدارة روبوت متعدد المكونات مع middleware مناسب.", [
                ("ROS2 Concepts", "nodes وtopics وservices", "تصميم graph لروبوت بسيط", "شرح تدفق البيانات."),
                ("Robot Communication", "serial وCAN وEthernet", "ربط controller برسالة command", "اختيار قناة اتصال مناسبة."),
                ("State Machines", "modes وtransitions وfault states", "تصميم state machine لعربة", "منع حالات غير صالحة."),
                ("Robot Simulation", "simulation-first workflow", "اختبار حركة في بيئة محاكاة", "استعمال المحاكاة قبل العتاد.")
            ]),
            ("الأسبوع 7: Computer Vision وAI للروبوتات", "تقديم طبقة الإدراك البصري والقرارات المعتمدة على البيانات.", [
                ("Camera Fundamentals", "frames وresolution وcalibration", "التقاط ومعاينة صور", "ضبط pipeline للكاميرا."),
                ("Image Processing", "thresholding وedges وcontours", "استخراج جسم من صورة", "فهم مراحل المعالجة."),
                ("Object Detection", "features وdetectors", "بناء prototype لاكتشاف هدف", "ربط detection بالقرار."),
                ("AI Safety", "confidence وfallbacks", "منع الروبوت من التحرك عند confidence منخفض", "دمج uncertainty في التحكم.")
            ]),
            ("الأسبوع 8: مشروع روبوت متكامل", "دمج الحساسات والتحكم والميكانيكا والبرمجيات في منظومة واحدة.", [
                ("System Architecture", "interfaces وsubsystems", "رسم architecture للروبوت", "تقسيم النظام إلى وحدات واضحة."),
                ("Integration وCalibration", "معايرة النظام كاملًا", "ربط sensor-controller-actuator", "تشخيص مشاكل التكامل."),
                ("Field Testing", "test plans وfailure logs", "تشغيل سلسلة اختبارات ميدانية", "تسجيل failures بصورة منهجية."),
                ("Capstone Demo", "توثيق النتائج والحدود", "عرض روبوت مع تقرير هندسي", "شرح النظام والدروس المستفادة.")
            ]),
        ],
    },
    "embedded-systems-microchip-programming": {
        "aliases": ["Embedded Systems & Microchip Programming", "برمجة الأنظمة المدمجة وشرائح السيليكون", "برمجة الأنظمة المدمجة وشرائح الميكروكنترولر"],
        "modules": [
            ("الأسبوع 1: Digital Electronics وMicrocontroller Foundations", "أساسيات المنطق الرقمي وإشارات الإدخال والإخراج.", [
                ("Binary وHex وBitwise", "التمثيل الثنائي والعمليات على البتات", "استخراج أعلام من register", "قراءة وكتابة masks."),
                ("GPIO", "input/output وpull-up وpull-down", "زر يتحكم في LED", "فهم حالات pin."),
                ("Registers", "memory mapped I/O", "تغيير GPIO عبر register", "ربط register بالعتاد."),
                ("Clock وReset", "clock tree وreset causes", "تحليل مصدر clock لمتحكم", "فهم أثر clock على peripheral.")
            ]),
            ("الأسبوع 2: C للأنظمة المدمجة", "كتابة C منخفضة المستوى مع مؤشرات وذاكرة بوعي.", [
                ("Pointers", "addresses وdereference", "تمرير buffer إلى دالة", "استخدام pointer بأمان."),
                ("Arrays وStructs", "data layout وembedded records", "تعريف packet struct", "توقع تمثيل البيانات."),
                ("volatile وconst", "compiler behavior وhardware registers", "تعريف register map", "منع compiler optimization الخطير."),
                ("Memory Safety", "stack/heap/bounds", "اكتشاف buffer bug", "تقليل مخاطر الذاكرة.")
            ]),
            ("الأسبوع 3: MCU Peripherals", "استخدام الوحدات الداخلية للمتحكم بترتيب هندسي.", [
                ("ADC", "sampling وresolution", "قراءة potentiometer", "تحويل ADC إلى قيمة هندسية."),
                ("DMA", "memory transfers", "نقل buffer بدون CPU loop", "معرفة متى تستخدم DMA."),
                ("Timers", "timer modes وcapture", "قياس زمن نبضة", "اختيار إعداد timer."),
                ("Watchdog", "fault recovery", "إعادة تشغيل عند hang", "تصميم recovery mechanism.")
            ]),
            ("الأسبوع 4: Interrupts وTimers وPWM", "كتابة firmware يستجيب للأحداث في الوقت الصحيح.", [
                ("Interrupt Model", "ISR وpriority وlatency", "التعامل مع external interrupt", "كتابة ISR صغيرة."),
                ("Debouncing", "mechanical bounce", "زر يولد interrupt موثوق", "معالجة noise الزمني."),
                ("PWM", "duty cycle وfrequency", "تحكم في motor/LED", "ربط PWM بالوظيفة."),
                ("Scheduling Basics", "time slots وtick", "scheduler بسيط بدون RTOS", "تقسيم المهام الزمنية.")
            ]),
            ("الأسبوع 5: UART وI2C وSPI وCAN", "ربط المتحكم مع العالم الخارجي عبر بروتوكولات صناعية شائعة.", [
                ("UART", "baud وframes وbuffers", "console serial", "تشخيص firmware عبر serial."),
                ("I2C", "addressing وmaster/slave", "قراءة sensor عبر I2C", "تتبع transaction."),
                ("SPI", "clock phase وchip select", "قراءة flash/ADC", "اختيار SPI configuration."),
                ("CAN", "frames وarbitration", "تصميم رسائل control", "فهم bus contention.")
            ]),
            ("الأسبوع 6: Bare-Metal وRTOS وDebugging", "اختيار أسلوب التنفيذ المناسب وإدارة المهام المتزامنة.", [
                ("Bare-Metal Architecture", "superloop وstate-driven firmware", "بناء loop لمنظومة صغيرة", "تقسيم المهام بوضوح."),
                ("RTOS Tasks", "tasks وqueues وsemaphores", "تصميم ثلاث مهام firmware", "فهم concurrency."),
                ("Race Conditions", "shared data وcritical sections", "إصلاح race بسيطة", "تحديد نقاط التزامن الخطرة."),
                ("JTAG/SWD Debugging", "breakpoints وwatch وtrace", "تشخيص crash", "تتبع fault حتى سببه.")
            ]),
            ("الأسبوع 7: PCB وBootloader وPower", "فهم الطبقات التي تجعل firmware قابلًا للشحن والإنتاج.", [
                ("PCB Awareness", "signal integrity وlayout basics", "مراجعة PCB صغيرة", "اكتشاف أخطاء تصميم واضحة."),
                ("Bootloaders", "flash layout وfirmware update", "تصميم تصور bootloader", "شرح مراحل الإقلاع."),
                ("Memory Mapping", "flash وRAM وstack", "تحليل linker map مبسط", "تحديد استهلاك الذاكرة."),
                ("Power Management", "sleep modes وcurrent budget", "تقليل استهلاك جهاز", "اختيار استراتيجية power.")
            ]),
            ("الأسبوع 8: Production Firmware Capstone", "بناء firmware موثوق مع اختبار وتوثيق وخطة إصدار.", [
                ("Firmware Architecture", "drivers وHAL وapplication layers", "تقسيم مشروع كامل", "إنشاء حدود layers."),
                ("Testing Embedded Code", "host tests وhardware-in-loop concept", "اختبار driver على host", "فصل المنطق عن العتاد."),
                ("Failure Analysis", "fault tree وlogging", "تحليل جهاز يعيد التشغيل", "تحديد السبب الجذري."),
                ("Capstone Release", "release image وdocumentation", "إصدار firmware موثق", "تسليم artifact قابل لإعادة البناء.")
            ]),
        ],
    },
    "programming-foundations-zero-to-hero": {
        "aliases": ["Programming Foundations: Zero to Hero", "أساسيات البرمجة: نقطة الانطلاق", "أساسيات البرمجة نقطة الانطلاق"],
        "modules": [
            ("الأسبوع 1: التفكير الحاسوبي", "تحويل المشاكل اليومية إلى خطوات وقرارات قابلة للبرمجة.", [
                ("ما هي البرمجة؟", "الخوارزمية والبرنامج والتنفيذ", "كتابة خوارزمية لتحضير وجبة", "التفريق بين المشكلة والحل."),
                ("المتغيرات والبيانات", "values وtypes", "تخزين بيانات طالب", "اختيار type مناسب."),
                ("الشروط", "if/elif/else", "حساب حالة نجاح طالب", "كتابة شروط واضحة."),
                ("التكرار", "loops والعدادات", "توليد تقرير بسيط", "استخدام loop دون تكرار يدوي.")
            ]),
            ("الأسبوع 2: أساسيات Python العملية", "بناء عادة كتابة برامج صغيرة تعمل من أول مبادئها.", [
                ("Input وOutput", "التفاعل مع المستخدم", "برنامج مصروفات", "بناء CLI بسيط."),
                ("Strings", "النصوص والبحث والتنسيق", "تنظيف أسماء المستخدمين", "معالجة text بأمان."),
                ("Numbers وBoolean", "الحساب والمقارنات", "حاسبة درجات", "دمج operations بشكل صحيح."),
                ("Mini Project 1", "دمج الأساسيات", "برنامج قائمة مهام نصية", "تجميع عدة مفاهيم في مشروع.")
            ]),
            ("الأسبوع 3: Functions وData Structures", "الانتقال إلى كود قابل لإعادة الاستخدام.", [
                ("الدوال", "parameters وreturn", "دوال حساب أسعار", "تقليل التكرار."),
                ("Lists", "تجميع العناصر والفهرسة", "إدارة قائمة طلاب", "معالجة مجموعة بيانات."),
                ("Dictionaries", "key/value", "ملف بيانات طالب", "الوصول المنظم للمعلومات."),
                ("اختيار بنية البيانات", "trade-offs البسيطة", "مقارنة list وdict لنفس المهمة", "تحديد structure مناسب.")
            ]),
            ("الأسبوع 4: OOP وModules وFiles", "تعلم تنظيم المشاريع الصغيرة في وحدات واضحة.", [
                ("الكائنات والأصناف", "class وinstance", "إنشاء Student class", "فهم state وbehavior."),
                ("Modules", "import وتنظيم الملفات", "تقسيم مشروع إلى modules", "فصل المسؤوليات."),
                ("Files وJSON", "قراءة وكتابة البيانات", "حفظ المهام في JSON", "بناء persistence بسيط."),
                ("Mini Project 2", "تجميع OOP والملفات", "برنامج إدارة مكتبة صغيرة", "بناء تطبيق متعدد الملفات.")
            ]),
            ("الأسبوع 5: Git وDebugging وTesting", "تعلم العادات التي تميز المطور المنظم.", [
                ("Git Basics", "commit وbranch وhistory", "إنشاء repo للمشاريع", "تتبع التغييرات."),
                ("Debugging", "قراءة traceback", "إصلاح bugs مقصودة", "الوصول للسبب الجذري."),
                ("اختبارات بسيطة", "assert وtest cases", "اختبار دوال مشروع", "منع regression."),
                ("Code Review", "naming وreadability", "مراجعة كود زميل افتراضي", "اكتشاف مشاكل maintainability.")
            ]),
            ("الأسبوع 6: Algorithms وData Structures", "بناء أساس خوارزمي يساعد على التفكير بكفاءة.", [
                ("Big O بصورة عملية", "time complexity", "مقارنة خوارزميتين للبحث", "تفسير الفرق دون حفظ أعمى."),
                ("Searching", "linear وbinary search", "تطبيق بحث على بيانات مرتبة", "اختيار الخوارزمية حسب البيانات."),
                ("Sorting", "مقارنة الخوارزميات", "ترتيب نتائج الطلاب", "فهم أثر sorting على الأداء."),
                ("Stacks وQueues", "LIFO وFIFO", "محاكاة طابور خدمة", "تحديد بنية البيانات المناسبة.")
            ]),
            ("الأسبوع 7: Web وAPIs وSQL للمبتدئين", "ربط البرمجة بالعالم الحقيقي والخدمات وقواعد البيانات.", [
                ("كيف يعمل الويب؟", "browser وserver وHTTP", "تتبع طلب صفحة", "شرح رحلة request."),
                ("REST API", "endpoints وJSON", "استهلاك API عامة", "قراءة API contract."),
                ("SQL Basics", "SELECT وINSERT وWHERE", "إنشاء جدول والبحث فيه", "كتابة query بسيطة."),
                ("ربط Python بالبيانات", "CRUD concept", "برنامج يقرأ سجلات", "فهم طبقة data access.")
            ]),
            ("الأسبوع 8: مشروع التخرج والاستعداد لسوق العمل", "تحويل المهارات إلى مشروع قابل للعرض والتطوير.", [
                ("اختيار فكرة المشروع", "scope وrequirements", "كتابة feature list", "تقليل scope إلى MVP."),
                ("تنفيذ MVP", "iteration وfeedback", "بناء نسخة أولى", "تحويل الخطة إلى برنامج يعمل."),
                ("تحسين الجودة", "refactor وtests وREADME", "تجهيز المشروع للنشر", "تسليم مشروع منظم."),
                ("Portfolio وInterview Basics", "عرض المشروع والتفكير الهندسي", "كتابة README وتحضير شرح", "شرح المشروع بثقة ووضوح.")
            ]),
        ],
    },
}


def find_track(session, spec: dict) -> Track | None:
    aliases = [normalize(value) for value in spec["aliases"]]
    stmt = select(Track).where(Track.slug == spec.get("slug", ""))
    track = session.scalar(stmt)
    if track:
        return track

    tracks = session.scalars(select(Track)).all()
    for candidate in tracks:
        if normalize(candidate.name) in aliases:
            return candidate
    return None


def upsert_curriculum(session, track: Track, modules: list) -> tuple[int, int]:
    module_count = 0
    lesson_count = 0

    existing_modules = list(
        session.scalars(
            select(TrackModule)
            .where(TrackModule.track_id == track.id)
            .order_by(TrackModule.ordering, TrackModule.id)
        ).all()
    )

    by_title = {normalize(module.title): module for module in existing_modules}

    for module_order, (module_title, module_description, lessons) in enumerate(modules, start=1):
        module = by_title.get(normalize(module_title))

        if module is None:
            module = TrackModule(
                track_id=track.id,
                title=module_title,
                description=module_description,
                ordering=module_order,
                is_active=True,
            )
            session.add(module)
            session.flush()
            by_title[normalize(module_title)] = module
            module_count += 1
        else:
            module.description = module_description
            module.ordering = module_order
            module.is_active = True

        existing_lessons = list(
            session.scalars(
                select(Lesson)
                .where(Lesson.module_id == module.id)
                .order_by(Lesson.ordering, Lesson.id)
            ).all()
        )
        lessons_by_title = {normalize(lesson.title): lesson for lesson in existing_lessons}

        for lesson_order, (lesson_title, focus, lab, outcome) in enumerate(lessons, start=1):
            content = lesson_content(
                track_name=track.name,
                module_title=module_title,
                lesson_title=lesson_title,
                focus=focus,
                lab=lab,
                outcome=outcome,
            )
            lesson = lessons_by_title.get(normalize(lesson_title))

            if lesson is None:
                session.add(
                    Lesson(
                        module_id=module.id,
                        title=lesson_title,
                        content=content,
                        video_url=None,
                        ordering=lesson_order,
                    )
                )
                lesson_count += 1
            else:
                lesson.content = content
                lesson.video_url = None
                lesson.ordering = lesson_order

    return module_count, lesson_count


def main() -> None:
    session = SessionLocal()
    total_modules = 0
    total_lessons = 0
    missing: list[str] = []

    try:
        for key, spec in CURRICULA.items():
            track = find_track(session, spec)
            if track is None:
                missing.append(key)
                continue

            created_modules, created_lessons = upsert_curriculum(
                session,
                track,
                spec["modules"],
            )
            total_modules += created_modules
            total_lessons += created_lessons
            print(
                f"✅ {track.name}: "
                f"{len(spec['modules'])} modules / "
                f"{sum(len(item[2]) for item in spec['modules'])} lessons "
                f"(created {created_modules} modules, {created_lessons} lessons)"
            )
            session.commit()

        if missing:
            session.rollback()
            raise RuntimeError(
                "Missing seeded tracks: " + ", ".join(missing)
            )

        print(
            f"🚀 Curriculum seeding complete: "
            f"{len(CURRICULA)} tracks, "
            f"{sum(len(spec['modules']) for spec in CURRICULA.values())} modules, "
            f"{sum(len(module[2]) for spec in CURRICULA.values() for module in spec['modules'])} lessons."
        )
        print(
            f"📌 New rows created in this run: "
            f"{total_modules} modules, {total_lessons} lessons."
        )

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
