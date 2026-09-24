import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.track import Track
from app.models.curriculum import TrackModule, Lesson # تأكد من أن هذه هي أسماء الموديلز الصحيحة لديك

def seed_curriculum():
    db = SessionLocal()
    try:
        tracks = db.query(Track).all()
        if not tracks:
            print("❌ لا يوجد مسارات! قم بتشغيل seed_academy.py أولاً.")
            return

        module_titles_templates = [
            "الوحدة 1: الأساسيات والانطلاق", "الوحدة 2: المفاهيم المتوسطة",
            "الوحدة 3: بناء الهيكلية والتصميم", "الوحدة 4: التطبيق العملي الأول",
            "الوحدة 5: المفاهيم المتقدمة", "الوحدة 6: التأمين وتحسين الأداء",
            "الوحدة 7: دمج التقنيات الحديثة", "الوحدة 8: مشروع التخرج الشامل"
        ]

        total_modules = 0
        total_lessons = 0

        for track in tracks:
            print(f"⏳ جاري بناء منهج: {track.name}...")
            
            # التأكد من عدم تكرار المنهج
            existing_modules = db.query(TrackModule).filter(TrackModule.track_id == track.id).count()
            if existing_modules > 0:
                print(f"⚠️ المنهج موجود بالفعل لمسار {track.name}. سيتم التخطي.")
                continue

            for order, mod_title in enumerate(module_titles_templates, start=1):
                new_module = TrackModule(
                    track_id=track.id,
                    title=f"{mod_title} - {track.name}",
                    description=f"في هذه الوحدة سنغطي أهم تفاصيل {mod_title} خطوة بخطوة.",
                    order=order
                )
                db.add(new_module)
                db.flush() # للحصول على new_module.id
                total_modules += 1

                for lesson_order in range(1, 5):
                    new_lesson = Lesson(
                        module_id=new_module.id,
                        title=f"الدرس {lesson_order}: الشرح التطبيقي",
                        content=f"هذا هو المحتوى التفصيلي للدرس رقم {lesson_order}. يحتوي على أمثلة عملية وشرح مبسط.",
                        order=lesson_order,
                        is_unlocked_for_preview=True if (order == 1 and lesson_order == 1) else False
                    )
                    db.add(new_lesson)
                    total_lessons += 1

        db.commit()
        print(f"🚀 اكتمل الزرع! تم إضافة {total_modules} وحدة و {total_lessons} درساً بنجاح.")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء زرع المنهج: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_curriculum()