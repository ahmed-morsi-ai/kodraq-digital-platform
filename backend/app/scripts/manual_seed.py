from app.core.pricing import BACKEND_AI_TRACK_PRICE_EGP
from app.db.session import SessionLocal
from app.models.track import Track, TrackModule

def seed_data():
    db = SessionLocal()
    try:
        # 1. إنشاء مسار الباك إند
        backend_track = Track(
            name="Backend & AI Engineering",  # تم تغيير title إلى name
            slug="backend-ai-engineering",    # تمت إضافة slug لأنه حقل إجباري
            description="Master Python, FastAPI, and AI RAG systems.",
            is_active=True,
            price=BACKEND_AI_TRACK_PRICE_EGP
        )
        db.add(backend_track)
        db.commit()
        db.refresh(backend_track)

        # 2. إنشاء الوحدات الأربع وربطها بالمسار
        modules = [
            # تم استخدام TrackModule بدلاً من Module
            # تم استخدام ordering بدلاً من order
            TrackModule(title="Module 00: Backend Mindset", track_id=backend_track.id, ordering=1),
            TrackModule(title="Module 01: Advanced Python", track_id=backend_track.id, ordering=2),
            TrackModule(title="Module 02: Clean Code & SOLID", track_id=backend_track.id, ordering=3),
            TrackModule(title="Module 03: HTTP & Networking", track_id=backend_track.id, ordering=4),
        ]
        db.add_all(modules)
        db.commit()
        print("✅ تم إضافة المسار والمناهج بنجاح!")
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()