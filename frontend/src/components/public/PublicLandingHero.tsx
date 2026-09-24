import { ArrowLeft, Briefcase, GraduationCap } from "lucide-react";
import { Link } from "react-router-dom";

export default function PublicLandingHero() {
  return (
    <section
      id="home"
      dir="rtl"
      className="relative min-h-screen overflow-hidden bg-white px-6 pb-20 pt-28 text-slate-900 md:px-12"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
        <div className="absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl">
        <div className="mx-auto mb-16 max-w-4xl text-center">
          <div className="mb-5 text-xs font-bold uppercase tracking-[0.3em] text-[#5B9BD5]">
            Kodraq Digital
          </div>

          <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 md:text-6xl">
            مستقبلك الرقمي يبدأ مع <span className="text-[#5B9BD5]">Kodraq</span>
          </h1>

          <p className="mx-auto max-w-3xl text-lg font-medium leading-relaxed text-slate-500 md:text-xl">
            سواء كنت تطمح لبناء مسيرتك في التقنية أو تبحث عن حلول برمجية ترتقي بأعمالك، Kodraq تساعدك على الانتقال من الفكرة إلى نتيجة حقيقية.
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-2">
          <Link
            to="/register?persona=trainee"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-[#BFDFFF] hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <GraduationCap size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا متدرب
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Academy
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                ابدأ رحلتك مع برامج تدريبية مكثفة في Technical Tracks حقيقية، وتعلّم من خلال Practical Tasks وProjects تساعدك على بناء مهاراتك والاستعداد لسوق العمل.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>ابدأ رحلتك التعليمية</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </Link>

          <Link
            to="/login?persona=client"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-[#BFDFFF] hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <Briefcase size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا عميل
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Services
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                حوّل فكرتك إلى Digital Product قابل للتوسع من خلال Web & Software Development وAI Automation وUI/UX وCloud Solutions مصممة باحتياجات عملك.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>اكتشف Kodraq Services</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </Link>
        </div>
      </div>
    </section>
  );
}