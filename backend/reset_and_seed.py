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

YOUTUBE_EMBED_PATTERN = re.compile(
    r"https://www\.youtube\.com/embed/[A-Za-z0-9_-]{11}"
)

BACKEND_AI_MODULES = [
    {
        "title": "Module 1: أساسيات الباك إند وبايثون المتقدمة",
        "description": "تأسيس قوي في Python وتصميم واجهات الباك إند والتحقق من البيانات وبناء تطبيقات قابلة للصيانة.",
        "ordering": 1,
        "lessons": [
            {
                "title": "مقدمة في هندسة الباك إند وPython",
                "description": "تعرّف على دور الباك إند في استقبال الطلبات وتنفيذ منطق التطبيق والتعامل مع قواعد البيانات وإرجاع استجابات واضحة وآمنة.",
                "content": "تشرح هذه الوحدة دورة حياة الطلب من العميل إلى الخادم ثم قاعدة البيانات والعودة. ستتعرف على مسؤوليات طبقة الباك إند، وكيف تساعد Python على بناء خدمات قابلة للاختبار والتوسع، مع التمييز بين منطق المجال وطبقة HTTP.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/rfscVS0vtbw",
            },
            {
                "title": "التحقق من البيانات باستخدام Pydantic",
                "description": "افهم كيف تحوّل نماذج Pydantic المدخلات الخارجية إلى بيانات موثوقة، وتفرض القيود، وتعرض أخطاء تحقق مفهومة.",
                "content": "ستبني نماذج typed للطلبات والاستجابات، وتستخدم الحقول المقيدة والتحقق من القيم الاختيارية والبيانات المتداخلة. قارن بين type hints التي تساعد الفحص الثابت والتحقق وقت التشغيل الذي يمنع البيانات غير الصالحة من دخول التطبيق.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/M81pfi64eeM",
            },
            {
                "title": "البرمجة غير المتزامنة Async/Await في Python",
                "description": "تعلّم استخدام coroutines وevent loop لتحسين التعامل مع عمليات الشبكة وI/O دون حجب بقية الطلبات.",
                "content": "تشرح المادة الفرق بين الدوال المتزامنة وغير المتزامنة، وكيفية انتظار عمليات I/O وإدارة الإلغاء والمهلات والأخطاء. ستتعرف أيضاً على الحالات التي لا يسرّع فيها async العمل، مثل الحسابات الثقيلة أو استدعاء مكتبات متزامنة حاجبة.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/t5Bo1Je9EmE",
            },
        ],
        "resources": [
            {"title": "FastAPI Cheat Sheet (PDF)", "file_url": "https://example.com/fastapi-cheatsheet.pdf", "resource_type": "pdf"}
        ],
    },
    {
        "title": "Module 2: قواعد البيانات وإدارة التخزين",
        "description": "صمّم قواعد بيانات PostgreSQL سليمة، واستخدم SQLAlchemy وAlembic لإدارة البيانات وتطور المخطط بأمان.",
        "ordering": 2,
        "lessons": [
            {
                "title": "تصميم قواعد بيانات PostgreSQL والعلاقات",
                "description": "تعرّف على تصميم الجداول والعلاقات والمفاتيح والقيود التي تحافظ على صحة البيانات في PostgreSQL.",
                "content": "ستحوّل متطلبات التطبيق إلى جداول مترابطة باستخدام المفاتيح الأساسية والخارجية، وتفهم التطبيع والعلاقات واحد إلى متعدد ومتعدد إلى متعدد. تتضمن المادة أمثلة على الفهارس والقيود والمعاملات وكيفية تجنب التكرار وحالات البيانات غير المتسقة.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/26ls5lNiijk",
            },
            {
                "title": "إدارة البيانات باستخدام SQLAlchemy ORM",
                "description": "استخدم نماذج SQLAlchemy والعلاقات والجلسات لتنفيذ استعلامات واضحة وإدارة المعاملات بكفاءة.",
                "content": "تشرح الوحدة ربط كائنات Python بالجداول، وكتابة الاستعلامات باستخدام واجهة SQLAlchemy 2.x، وإدارة Session وحدود المعاملة. ستقارن استراتيجيات تحميل العلاقات وتتعرف على مشكلة N+1 وكيفية اختيار التحميل المناسب.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/529LYDgRTgQ",
            },
            {
                "title": "ترحيل مخطط قاعدة البيانات باستخدام Alembic",
                "description": "تعلّم إنشاء مراجعات Alembic ومراجعتها وتطبيقها أو التراجع عنها دون فقدان بيانات البيئة.",
                "content": "ستربط Alembic ببيانات SQLAlchemy الوصفية، وتنشئ migrations لتغييرات المخطط، ثم تراجع SQL الناتج قبل التطبيق. توضح المادة ترتيب الترحيلات، وكتابة التغييرات القابلة للعكس، والتعامل مع تحديثات البيانات والتوافق بين إصدارات التطبيق.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/e8NnDz8uT7o",
            },
        ],
        "resources": [
            {"title": "SQL & PostgreSQL Optimization Guide", "file_url": "https://example.com/sql-guide.pdf", "resource_type": "pdf"}
        ],
    },
    {
        "title": "Module 3: هندسة الذكاء الاصطناعي وأنظمة RAG",
        "description": "ابنِ ميزات ذكاء اصطناعي تربط النماذج اللغوية بالبحث الدلالي ومصادر المعرفة مع الحفاظ على موثوقية الإجابات.",
        "ordering": 3,
        "lessons": [
            {
                "title": "أساسيات نماذج اللغة الكبيرة وصياغة الأوامر",
                "description": "افهم طريقة عمل نماذج اللغة الكبيرة، وصمّم prompts واضحة تحدد المهمة والسياق وشكل الإجابة المطلوبة.",
                "content": "تقدم هذه المادة المفاهيم الأساسية للشبكات العصبية ونماذج اللغة، ثم تشرح بناء prompt يحدد الدور والمهمة والسياق والقيود. ستتعلم فصل التعليمات عن بيانات المستخدم، وتقييم المخرجات، ومعالجة الإجابات غير الدقيقة بأمان.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/aircAruvnKk",
            },
            {
                "title": "Embeddings وقواعد البيانات المتجهة",
                "description": "تعلّم تمثيل النصوص كمتجهات رقمية واستخدام التشابه الدلالي لاسترجاع المقاطع ذات الصلة.",
                "content": "تشرح الوحدة تحويل النص إلى embeddings، وتقسيم المستندات إلى مقاطع، وتخزين المتجهات مع بياناتها الوصفية. ستتعرف على البحث بالتشابه، واختيار حجم المقاطع، وتصفية النتائج بحسب المسار أو المستخدم لضمان أن الاسترجاع مناسب ومصرح به.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/klTvEwg3oJ4",
            },
            {
                "title": "بناء نظام RAG متكامل وربطه بالباك إند",
                "description": "اربط الاسترجاع الدلالي بنموذج لغوي لإنتاج إجابات مستندة إلى محتوى موثوق مع توضيح حدود الأدلة.",
                "content": "ستبني مسار RAG يبدأ باسترجاع المقاطع المناسبة، ثم يمررها إلى النموذج ضمن حدود سياق واضحة. تغطي المادة عزل مصادر المعرفة، ورفض الإجابة عند غياب الأدلة، وإرجاع المراجع، وقياس جودة الاسترجاع والدقة والتكلفة وزمن الاستجابة.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/T-D1OfcDW1M",
            },
        ],
        "resources": [
            {"title": "RAG Architecture Blueprint", "file_url": "https://example.com/rag-blueprint.pdf", "resource_type": "pdf"}
        ],
    },
    {
        "title": "Module 04: Production and Deployment",
        "description": "جهّز خدمات الباك إند للإنتاج باستخدام الحاويات وإدارة الإعدادات والفحوصات وخطوات النشر المستمر.",
        "ordering": 4,
        "lessons": [
            {
                "title": "إنشاء حاويات Docker لخدمة FastAPI",
                "description": "تعلّم بناء صورة Docker صغيرة وقابلة للتكرار وتشغيل خدمة FastAPI بإعدادات آمنة وفحوصات صحة واضحة.",
                "content": "تشرح المادة كتابة Dockerfile، واختيار صورة أساس مناسبة، وتثبيت الاعتماديات، وتشغيل التطبيق بعملية رئيسية صحيحة. ستتعرف على تمرير الإعدادات وقت التشغيل، وعدم تضمين الأسرار في الصورة، وإضافة health checks ومستخدم تشغيل محدود الصلاحيات.",
                "ordering": 1,
                "video_url": "https://www.youtube.com/embed/3c-iBn73dDE",
            },
            {
                "title": "تشغيل الخدمات باستخدام Docker Compose",
                "description": "نسّق خدمة API وقاعدة البيانات والشبكات والأحجام الدائمة باستخدام Docker Compose محلياً وبشكل قابل للتكرار.",
                "content": "ستعرّف خدمات التطبيق وقاعدة البيانات في ملف Compose، وتضبط الشبكات ومتغيرات البيئة والأحجام الدائمة وفحوصات الجاهزية. توضح الوحدة الفرق بين ترتيب بدء الحاويات وجاهزية الخدمة، وكيفية فحص السجلات وتشخيص أعطال الاتصال.",
                "ordering": 2,
                "video_url": "https://www.youtube.com/embed/HG6yIjZapSA",
            },
            {
                "title": "خطوط CI/CD والنشر ومراقبة الخدمة",
                "description": "أنشئ خط CI/CD يشغّل الفحوصات ويبني artifact موثوقاً قبل النشر، ثم راقب صحة الخدمة بعد الإصدار.",
                "content": "تغطي المادة مراحل التحقق الآلي والاختبارات وبناء صورة الإصدار ونشرها، مع إدارة الأسرار خارج المستودع. ستخطط لترحيلات قاعدة البيانات وفحوصات readiness وliveness، وتتعلم التراجع عن إصدار معيب ومراجعة السجلات ومؤشرات الأداء بعد النشر.",
                "ordering": 3,
                "video_url": "https://www.youtube.com/embed/R8_veQiYBjI",
            },
        ],
    },
]


def validate_curriculum_data() -> None:
    expected_orders = [1, 2, 3, 4]
    actual_orders = [module.get("ordering") for module in BACKEND_AI_MODULES]
    if actual_orders != expected_orders:
        raise ValueError("Backend & AI curriculum must contain modules 1 through 4 in order.")

    for module in BACKEND_AI_MODULES:
        lessons = module.get("lessons")
        if not isinstance(lessons, list) or not lessons:
            raise ValueError(f"Module {module.get('ordering')} must contain lessons.")
        for lesson in lessons:
            required_fields = {"title", "description", "content", "ordering", "video_url"}
            missing_fields = required_fields - lesson.keys()
            if missing_fields:
                raise ValueError(
                    f"Lesson {lesson.get('title')} is missing fields: "
                    f"{', '.join(sorted(missing_fields))}."
                )
            description = lesson.get("description")
            content = lesson.get("content")
            video_url = lesson.get("video_url")
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"Lesson {lesson.get('title')} must have a description.")
            if not re.search(r"[\u0600-\u06ff]", description):
                raise ValueError(f"Lesson {lesson.get('title')} description must be Arabic.")
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"Lesson {lesson.get('title')} must have content.")
            if not isinstance(video_url, str) or not YOUTUBE_EMBED_PATTERN.fullmatch(video_url):
                raise ValueError(f"Lesson {lesson.get('title')} must have a YouTube embed URL.")


def reset_and_seed():
    from app.models.enrollment import Enrollment
    from app.models.track import Lesson, Resource, Track, TrackModule
    from app.models.user import User

    validate_curriculum_data()
    print("🧹 Cleaning existing database (users, enrollments, tracks, modules)...")
    try:
        with SessionLocal.begin() as db:
            db.query(Enrollment).delete()
            db.query(Resource).delete()
            db.query(Lesson).delete()
            db.query(TrackModule).delete()
            db.query(Track).delete()
            db.query(User).delete()

            tracks_data = [
                {
                    "name": "هندسة الباك إند والذكاء الاصطناعي",
                    "slug": "backend-ai-engineering",
                    "description": "مسار متكامل من الصفر للاحتراف. تعلم بناء أنظمة قوية باستخدام Python و PostgreSQL و FastAPI، مع دمج نماذج الذكاء الاصطناعي (RAG) وتصميم قواعد البيانات المتقدمة.",
                    "ordering": 1,
                    "is_premium": True,
                    "price": 5400.00,
                    "currency": "EGP",
                    "is_active": True,
                },
                {
                    "name": "برمجة الأنظمة المدمجة وشرائح السيليكون",
                    "slug": "embedded-systems-microchips",
                    "description": "احتراف لغة C/C++، التعامل العميق مع متحكمات ARM Cortex-M، برمجة أنظمة الزمن الفعلية (RTOS)، وتصميم اللوحة المطبوعة (PCB Design) كمهندس محترف.",
                    "ordering": 2,
                    "is_premium": True,
                    "price": 600.00,
                    "currency": "EGP",
                    "is_active": True,
                },
                {
                    "name": "دبلومة الميكاترونكس والروبوتات",
                    "slug": "mechatronics-robotics",
                    "description": "من الأساسيات الفيزيائية إلى أنظمة التحكم المتقدمة، تصميم وبرمجة الروبوتات الذكية، استيعاب الـ ROS، وتطبيقات إنترنت الأشياء (IoT) للتحكم الصناعي.",
                    "ordering": 3,
                    "is_premium": True,
                    "price": 550.00,
                    "currency": "EGP",
                    "is_active": True,
                },
            ]

            created_tracks = {}
            for track_data in tracks_data:
                track = Track(**track_data)
                db.add(track)
                db.flush()
                created_tracks[track.slug] = track
                print(
                    f"✅ Created track: {track.name} (ID: {track.id}, "
                    f"Premium: {track.is_premium}, Price: {track.price} {track.currency})"
                )

            ai_track = created_tracks["backend-ai-engineering"]
            expected_lesson_count = sum(
                len(module_data["lessons"]) for module_data in BACKEND_AI_MODULES
            )
            for module_data in BACKEND_AI_MODULES:
                module = TrackModule(
                    track_id=ai_track.id,
                    title=module_data["title"],
                    description=module_data["description"],
                    ordering=module_data["ordering"],
                )
                db.add(module)
                db.flush()

                for lesson_data in module_data["lessons"]:
                    db.add(Lesson(module_id=module.id, **lesson_data))
                for resource_data in module_data.get("resources", []):
                    db.add(Resource(module_id=module.id, **resource_data))

            db.flush()
            seeded_lessons = (
                db.query(Lesson)
                .join(TrackModule, Lesson.module_id == TrackModule.id)
                .filter(TrackModule.track_id == ai_track.id)
                .all()
            )
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

        print("✨ Existing data was cleaned and the database transaction committed.")
        print("🚀 Successfully reset DB and seeded four complete Backend & AI modules!")
    except Exception as e:
        print(f"❌ Error during reset and seed: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    reset_and_seed()