from __future__ import annotations
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.track import Track, TrackModule, Lesson, Resource
from app.models.enrollment import Enrollment

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.iypwblpjhmdjhspcuthl:morsi2007@AHMED@aws-1-eu-west-1.pooler.supabase.com:5432/postgres")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reset_and_seed():
    db = SessionLocal()
    try:
        print("🧹 Cleaning existing database (users, enrollments, tracks, modules)...")
        db.query(Enrollment).delete()
        db.query(Resource).delete()
        db.query(Lesson).delete()
        db.query(TrackModule).delete()
        db.query(Track).delete()
        db.query(User).delete()
        db.commit()
        print("✨ All previous accounts and data deleted successfully!")

        print("🌱 Re-creating tracks with Premium status for Backend & AI Engineering...")
        
        tracks_data = [
            {
                "name": "هندسة الباك إند والذكاء الاصطناعي",
                "slug": "backend-ai-engineering",
                "description": "مسار متكامل من الصفر للاحتراف. تعلم بناء أنظمة قوية باستخدام Python و PostgreSQL و FastAPI، مع دمج نماذج الذكاء الاصطناعي (RAG) وتصميم قواعد البيانات المتقدمة.",
                "ordering": 1,
                "is_premium": True,
                "price": 5400.00,  # <--- قم بتعديل السعر هنا
                "currency": "EGP",
                "is_active": True
            },
            # ... بقية المسارات
            {
                "name": "برمجة الأنظمة المدمجة وشرائح السيليكون",
                "slug": "embedded-systems-microchips",
                "description": "احتراف لغة C/C++، التعامل العميق مع متحكمات ARM Cortex-M، برمجة أنظمة الزمن الفعلية (RTOS)، وتصميم اللوحة المطبوعة (PCB Design) كمهندس محترف.",
                "ordering": 2,
                "is_premium": True,
                "price": 600.00,
                "currency": "EGP",
                "is_active": True
            },
            {
                "name": "دبلومة الميكاترونكس والروبوتات",
                "slug": "mechatronics-robotics",
                "description": "من الأساسيات الفيزيائية إلى أنظمة التحكم المتقدمة، تصميم وبرمجة الروبوتات الذكية، استيعاب الـ ROS، وتطبيقات إنترنت الأشياء (IoT) للتحكم الصناعي.",
                "ordering": 3,
                "is_premium": True,
                "price": 550.00,
                "currency": "EGP",
                "is_active": True
            }
        ]

        created_tracks = {}
        for t_data in tracks_data:
            track = Track(**t_data)
            db.add(track)
            db.commit()
            db.refresh(track)
            created_tracks[track.slug] = track
            print(f"✅ Created track: {track.name} (ID: {track.id}, Premium: {track.is_premium}, Price: {track.price} {track.currency})")

        # Seed curriculum for backend-ai-engineering
        ai_track = created_tracks["backend-ai-engineering"]
        modules_data = [
            {
                "title": "أساسيات الباك إند وبايثون المتقدمة",
                "description": "احتراف لغة بايثون المتقدمة وبناء واجهات برمجية عالية الأداء باستخدام FastAPI وتوثيقها.",
                "ordering": 1,
                "lessons": [
                    {"title": "مقدمة في هندسة الباك إند الحديثة", "content": "تعريف بهندسة البرمجيات الخلفية ودورة حياة الطلب والاستجابة.", "ordering": 1, "video_url": "https://www.youtube.com/watch?v=example1"},
                    {"title": "البرمجة غير المتزامنة Async/Await في بايثون", "content": "كيف تتعامل مع العمليات المتزامنة وغير المتزامنة لتحسين الأداء.", "ordering": 2, "video_url": "https://www.youtube.com/watch?v=example2"},
                    {"title": "التحقق من البيانات باستخدام Pydantic V2", "content": "فهم عميق لأنظمة النماذج والتحقق من صحة البيانات.", "ordering": 3, "video_url": "https://www.youtube.com/watch?v=example3"}
                ],
                "resources": [
                    {"title": "FastAPI Cheat Sheet (PDF)", "file_url": "https://example.com/fastapi-cheatsheet.pdf", "resource_type": "pdf"}
                ]
            },
            {
                "title": "قواعد البيانات وإدارة التخزين المتقدمة",
                "description": "تصميم قواعد البيانات العلاقية PostgreSQL، تحسين الأداء وإدارة الترحيل.",
                "ordering": 2,
                "lessons": [
                    {"title": "تصميم قواعد بيانات PostgreSQL احترافية", "content": "العلاقات بين الجداول (1-to-Many, Many-to-Many) والمفاتيح.", "ordering": 1, "video_url": "https://www.youtube.com/watch?v=example4"},
                    {"title": "إدارة الترحيل باستخدام Alembic و SQLAlchemy", "content": "كيفية تتبع التغيرات في بنية قاعدة البيانات وتحديثها بسلاسة.", "ordering": 2, "video_url": "https://www.youtube.com/watch?v=example5"}
                ],
                "resources": [
                    {"title": "SQL & PostgreSQL Optimization Guide", "file_url": "https://example.com/sql-guide.pdf", "resource_type": "pdf"}
                ]
            },
            {
                "title": "هندسة الذكاء الاصطناعي وتكامل أنظمة RAG",
                "description": "بناء أنظمة ذكية تجمع بين النماذج اللغوية وقواعد البيانات المتجهة للبحث الدلالي.",
                "ordering": 3,
                "lessons": [
                    {"title": "أساسيات نماذج اللغات الكبيرة وصياغة الأوامر", "content": "كيفية صياغة الأوامر باحترافية واستخدام System Prompts.", "ordering": 1, "video_url": "https://www.youtube.com/watch?v=example6"},
                    {"title": "قواعد البيانات المتجهة Vector Databases", "content": "فهم التحويل الدلالي للنصوص وكيفية تخزينها والبحث فيها.", "ordering": 2, "video_url": "https://www.youtube.com/watch?v=example7"},
                    {"title": "بناء نظام RAG متكامل وتوصيله بالباك إند", "content": "ربط نماذج الذكاء الاصطناعي بقاعدة بيانات وملفات الشركة.", "ordering": 3, "video_url": "https://www.youtube.com/watch?v=example8"}
                ],
                "resources": [
                    {"title": "RAG Architecture Blueprint", "file_url": "https://example.com/rag-blueprint.pdf", "resource_type": "pdf"}
                ]
            }
        ]

        for mod_data in modules_data:
            module = TrackModule(
                track_id=ai_track.id,
                title=mod_data["title"],
                description=mod_data["description"],
                ordering=mod_data["ordering"]
            )
            db.add(module)
            db.commit()
            db.refresh(module)

            for les_data in mod_data["lessons"]:
                db.add(Lesson(module_id=module.id, **les_data))
            for res_data in mod_data["resources"]:
                db.add(Resource(module_id=module.id, **res_data))
            db.commit()

        print("🚀 Successfully reset DB and seeded Premium Backend & AI track with curriculum!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during reset and seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_and_seed()