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
                "title": "البرمجة غير المتزامنة Async/Await في Python",
                "description": "تعرّف على coroutines وevent loop وكيفية استخدام await لتنفيذ عمليات الشبكة وI/O بكفاءة، مع فهم الإلغاء والمهلات ومعالجة الأخطاء ومتى لا يكون async مناسباً.",
                "content": "تبدأ المادة بالفرق بين الدالة العادية وasync def، ثم تشرح إنشاء coroutine وتشغيلها وانتظارها باستخدام await. ستتدرب على تشغيل عدة مهام I/O بالتزامن، وإضافة timeout، والتعامل مع cancellation والاستثناءات. كما ستتعلم لماذا لا يؤدي async تلقائياً إلى تسريع العمليات الحسابية، وكيف يمكن لاستدعاء مكتبة متزامنة حاجبة أن يوقف event loop، وكيف تختار بين تنفيذ متزامن وغير متزامن وفق طبيعة العمل.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/t5Bo1Je9EmE",
            },
            {
                "title": "بناء واجهات API باستخدام FastAPI",
                "description": "تعلّم تنظيم مشروع FastAPI وبناء endpoints واضحة مع dependency injection والتوثيق التلقائي واختبارات تغطي الاستجابات والأخطاء.",
                "content": "تشرح الوحدة تقسيم التطبيق إلى routers وschemas وservices وCRUD، وتعريف مسارات GET وPOST مع path وquery parameters وrequest bodies. ستستخدم dependencies لمشاركة جلسة قاعدة البيانات والتحقق من المستخدم، وتضبط status codes والاستجابات وتفحص OpenAPI. كما ستضيف اختبارات للمدخلات الصحيحة والخاطئة، وتتعرف على الفرق بين دوال المسار المتزامنة وغير المتزامنة وكيفية تجنب حجب event loop.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/SR5NYCdzKkc",
            },
            {
                "title": "التحقق من البيانات باستخدام Pydantic V2",
                "description": "افهم نماذج Pydantic V2 وحقولها المقيدة وعمليات serialization والتحقق المخصص لبناء حدود آمنة بين API وبيانات التطبيق.",
                "content": "ستنشئ BaseModel لمدخلات ومخرجات API، وتحدد أنواع الحقول والقيم الافتراضية والقيود باستخدام Field. تتناول المادة الحقول الاختيارية والنماذج المتداخلة وfield_validator وmodel_validator، ثم تشرح تحويل البيانات باستخدام model_validate وmodel_dump. ستفرق بين type hints المستخدمة للفحص الثابت والتحقق الفعلي وقت التشغيل، وتكتب اختبارات للحالات الصحيحة والقيم المفقودة والمدخلات غير الصالحة مع رسائل أخطاء مفيدة.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/M81pfi64eeM",
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