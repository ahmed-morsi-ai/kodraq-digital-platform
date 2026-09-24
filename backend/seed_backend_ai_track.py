from __future__ import annotations
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.track import Track, TrackModule, Lesson, Resource

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_track():
    db = SessionLocal()
    try:
        # Find the track by slug
        track = db.query(Track).filter(Track.slug == "backend-ai-engineering").first()
        if not track:
            print("❌ Track 'backend-ai-engineering' not found! Please make sure tracks are seeded first.")
            return

        print(f"✅ Found track: {track.name} (ID: {track.id})")

        # Check if modules already exist
        if track.modules:
            print("⚠️ Track already has modules. Skipping seeding to avoid duplicates.")
            return

        # Define modules, lessons, and resources
        modules_data = [
            {
                "title": "أساسيات الباك إند وبايثون المتقدمة",
                "description": "احتراف لغة بايثون المتقدمة وبناء واجهات برمجية عالية الأداء باستخدام FastAPI وتوثيقها.",
                "ordering": 1,
                "lessons": [
                    {
                        "title": "مقدمة في هندسة الباك إند الحديثة", 
                        "content": "تعريف بهندسة البرمجيات الخلفية، دورة حياة الطلب والاستجابة (Request/Response Lifecycle)، ومعايير RESTful APIs.", 
                        "ordering": 1, 
                        "video_url": "https://www.youtube.com/watch?v=example1"
                    },
                    {
                        "title": "البرمجة غير المتزامنة Async/Await في بايثون", 
                        "content": "كيف تتعامل مع العمليات المتزامنة وغير المتزامنة لتحسين أداء السيرفر ومعالجة آلاف الطلبات في نفس الوقت.", 
                        "ordering": 2, 
                        "video_url": "https://www.youtube.com/watch?v=example2"
                    },
                    {
                        "title": "التحقق من البيانات باستخدام Pydantic V2", 
                        "content": "فهم عميق لأنظمة النماذج والتحقق من صحة البيانات المدخلة والمخرجة لضمان أمان وسلامة النظام.", 
                        "ordering": 3, 
                        "video_url": "https://www.youtube.com/watch?v=example3"
                    }
                ],
                "resources": [
                    {"title": "FastAPI Cheat Sheet (PDF)", "file_url": "https://example.com/fastapi-cheatsheet.pdf", "resource_type": "pdf"}
                ]
            },
            {
                "title": "قواعد البيانات وإدارة التخزين المتقدمة",
                "description": "تصميم قواعد البيانات العلاقية PostgreSQL، تحسين الأداء باستخدام الفهارس، وإدارة الترحيل بسلامة.",
                "ordering": 2,
                "lessons": [
                    {
                        "title": "تصميم قواعد بيانات PostgreSQL احترافية", 
                        "content": "العلاقات بين الجداول (1-to-Many, Many-to-Many)، المفاتيح الأساسية والأجنبية، وتحسين استعلامات SQL.", 
                        "ordering": 1, 
                        "video_url": "https://www.youtube.com/watch?v=example4"
                    },
                    {
                        "title": "إدارة الترحيل باستخدام Alembic و SQLAlchemy", 
                        "content": "كيفية تتبع التغيرات في بنية قاعدة البيانات وتحديثها بسلاسة في بيئة الإنتاج دون فقدان البيانات.", 
                        "ordering": 2, 
                        "video_url": "https://www.youtube.com/watch?v=example5"
                    }
                ],
                "resources": [
                    {"title": "SQL & PostgreSQL Optimization Guide", "file_url": "https://example.com/sql-guide.pdf", "resource_type": "pdf"}
                ]
            },
            {
                "title": "هندسة الذكاء الاصطناعي وتكامل أنظمة RAG",
                "description": "بناء أنظمة ذكية تجمع بين النماذج اللغوية الكبيرة (LLMs) وقواعد البيانات المتجهة للبحث الدلالي.",
                "ordering": 3,
                "lessons": [
                    {
                        "title": "أساسيات نماذج اللغات الكبيرة وصياغة الأوامر (Prompt Engineering)", 
                        "content": "كيفية صياغة الأوامر باحترافية، استخدام الـ System Prompts، والحصول على مخرجات منظمة من الذكاء الاصطناعي.", 
                        "ordering": 1, 
                        "video_url": "https://www.youtube.com/watch?v=example6"
                    },
                    {
                        "title": "قواعد البيانات المتجهة Vector Databases و Embeddings", 
                        "content": "فهم التحويل الدلالي للنصوص وكيفية تخزينها والبحث فيها باستخدام قواعد بيانات متجهة.", 
                        "ordering": 2, 
                        "video_url": "https://www.youtube.com/watch?v=example7"
                    },
                    {
                        "title": "بناء نظام RAG متكامل وتوصيله بالباك إند", 
                        "content": "ربط نماذج الذكاء الاصطناعي بقاعدة بيانات وملفات الشركة لتوليد إجابات دقيقة وموثوقة (Retrieval-Augmented Generation).", 
                        "ordering": 3, 
                        "video_url": "https://www.youtube.com/watch?v=example8"
                    }
                ],
                "resources": [
                    {"title": "RAG Architecture Blueprint", "file_url": "https://example.com/rag-blueprint.pdf", "resource_type": "pdf"}
                ]
            }
        ]

        for mod_data in modules_data:
            module = TrackModule(
                track_id=track.id,
                title=mod_data["title"],
                description=mod_data["description"],
                ordering=mod_data["ordering"]
            )
            db.add(module)
            db.commit()
            db.refresh(module)

            # Add lessons
            for les_data in mod_data["lessons"]:
                lesson = Lesson(
                    module_id=module.id,
                    title=les_data["title"],
                    content=les_data["content"],
                    ordering=les_data["ordering"],
                    video_url=les_data.get("video_url")
                )
                db.add(lesson)

            # Add resources
            for res_data in mod_data["resources"]:
                resource = Resource(
                    module_id=module.id,
                    title=res_data["title"],
                    file_url=res_data["file_url"],
                    resource_type=res_data["resource_type"]
                )
                db.add(resource)

            db.commit()

        print("🚀 Successfully seeded curriculum for Backend & AI Engineering track!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding track: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_track()