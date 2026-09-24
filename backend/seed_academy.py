import sys
import os

# إضافة المسار الحالي ليتعرف بايثون على مجلد app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.track import Track

def seed_data():
    db = SessionLocal()
    try:
        tracks = [
            Track(
                name="هندسة الباك إند والذكاء الاصطناعي",
                slug="backend-ai-engineering",
                description="مسار متكامل من الصفر للاحتراف. تعلم بناء أنظمة قوية باستخدام Python و FastAPI و PostgreSQL، مع دمج نماذج الذكاء الاصطناعي (RAG) وتصميم قواعد البيانات المتقدمة.",
                is_premium=True,
                price=1500,
                currency="EGP"
            ),
            Track(
                name="دبلومة الميكاترونكس والروبوتات",
                slug="mechatronics-robotics",
                description="من الأساسيات الفيزيائية إلى أنظمة التحكم المتقدمة. تصميم وبرمجة الروبوتات الذكية، استيعاب الـ ROS، وتطبيقات إنترنت الأشياء (IoT) للتحكم الصناعي.",
                is_premium=True,
                price=2500,
                currency="EGP"
            ),
            Track(
                name="برمجة الأنظمة المدمجة وشرائح السيليكون",
                slug="embedded-systems-microchips",
                description="احتراف لغة C/C++، التعامل العميق مع متحكمات ARM Cortex-M، برمجة أنظمة الزمن الفعلي (RTOS)، وتصميم اللوحات المطبوعة (PCB Design) كمهندس محترف.",
                is_premium=True,
                price=3000,
                currency="EGP"
            ),
            Track(
                name="هندسة الواجهات الأمامية المتقدمة",
                slug="advanced-frontend",
                description="احترف بناء واجهات مستخدم معقدة باستخدام React و Next.js و TypeScript. تعلم إدارة الحالة، وتأمين التوافقية، وربط الـ APIs بكفاءة وسرعة فائقة.",
                is_premium=True,
                price=1200,
                currency="EGP"
            ),
            Track(
                name="أساسيات البرمجة: نقطة الانطلاق",
                slug="programming-foundations",
                description="المدخل الأساسي لعالم هندسة البرمجيات. تعلم المنطق البرمجي، الخوارزميات، وهياكل البيانات باستخدام C و Python. مسار مجاني بالكامل.",
                is_premium=False,
                price=0,
                currency="EGP"
            )
        ]

        for t in tracks:
            # التأكد من عدم تكرار المسار إذا تم تشغيل السكريبت مرتين
            existing = db.query(Track).filter(Track.slug == t.slug).first()
            if not existing:
                db.add(t)
                print(f"✅ تم إضافة مسار: {t.name}")
        
        db.commit()
        print("🚀 تم زرع الأكاديمية بالمسارات بنجاح!")
    
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()