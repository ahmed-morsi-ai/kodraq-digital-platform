import { ArrowUpRight, BriefcaseBusiness, Code2 } from "lucide-react";
import { Link } from "react-router-dom";

import PublicLandingHero from "@/components/public/PublicLandingHero";

import CinematicIntro from "@/components/public/CinematicIntro";

const services = [
  "Web & Software Development",
  "AI Automation & RAG",
  "AI Chatbots",
  "Dashboards & Internal Systems",
  "UI/UX & Product Design",
  "DevOps & Cloud Infrastructure",
];

export default function Landing() {
  return (
    <div
      dir="rtl"
      className="min-h-screen overflow-x-hidden bg-[#050817] text-white"
    >
      <CinematicIntro />

      <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/10 text-sm font-black text-emerald-300 shadow-[0_0_28px_rgba(16,185,129,0.12)]">
              KD
            </div>

            <div>
              <div className="text-sm font-black tracking-tight text-slate-900">Kodraq Digital</div>
              <div className="text-[10px] uppercase tracking-[0.32em] text-slate-400">
                Learn. Build. Automate.
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm text-slate-500 md:flex">
            <a className="transition hover:text-slate-900" href="#home">
              الرئيسية
            </a>
            <a className="transition hover:text-slate-900" href="#paths">
              Tracks
            </a>
            <a className="transition hover:text-slate-900" href="#services">
              الخدمات
            </a>
            <a className="transition hover:text-slate-900" href="#how-it-works">
              كيف نعمل
            </a>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/login?persona=trainee"
              className="hidden rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold text-white/75 transition hover:bg-white/[0.08] hover:text-white sm:inline-flex"
            >
              دخول
            </Link>

            <a
              href="#paths"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-300 to-cyan-300 px-4 py-2 text-xs font-black text-slate-950 shadow-[0_0_30px_rgba(16,185,129,0.16)] transition hover:-translate-y-0.5"
            >
              ابدأ الآن
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </header>

      <main>
        <PublicLandingHero />

        <section id="paths"
          className="relative border-y border-white/[0.06] bg-[#07111d] py-20"
        >
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                Choose Your Path
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                مساران. One Platform.
              </h2>
              <p className="mt-4 text-sm leading-7 text-white/45 sm:text-base">
                سواء كنت تبني مستقبلك التقني أو تبني منتجًا لشركتك، Kodraq مصممة
                لتأخذك من المتطلبات إلى نتيجة حقيقية.
              </p>
            </div>

            <div className="mt-10 grid gap-5 lg:grid-cols-2">
              <Link
                to="/login?persona=trainee"
                className="group rounded-[28px] border border-emerald-300/10 bg-gradient-to-br from-emerald-300/[0.08] to-transparent p-7 transition hover:-translate-y-1 hover:border-emerald-300/25"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-300/10 text-emerald-200">
                    <Code2 className="h-6 w-6" />
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-white/25 transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-emerald-200" />
                </div>

                <h3 className="mt-7 text-2xl font-black">أنا متدرب</h3>

                <p className="mt-3 max-w-xl text-sm leading-7 text-white/45">
                  اختر تخصصك، تعلّم بشكل مكثف، استخدم الـAI Tutor، نفّذ المهام،
                  وابنِ مشروعًا حقيقيًا يثبت قدراتك.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  {["Tracks", "AI Tutor", "Tasks", "Projects", "Certification"].map(
                    (item) => (
                      <span
                        key={item}
                        className="rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-[11px] text-white/50"
                      >
                        {item}
                      </span>
                    ),
                  )}
                </div>
              </Link>

              <a
                href="#services"
                className="group rounded-[28px] border border-cyan-300/10 bg-gradient-to-br from-cyan-300/[0.08] to-transparent p-7 transition hover:-translate-y-1 hover:border-cyan-300/25"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-300/10 text-cyan-200">
                    <BriefcaseBusiness className="h-6 w-6" />
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-white/25 transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-cyan-200" />
                </div>

                <h3 className="mt-7 text-2xl font-black">أنا عميل</h3>

                <p className="mt-3 max-w-xl text-sm leading-7 text-white/45">
                  اشرح فكرتك، دع Kodraq تفهم المتطلبات، تبني الـscope، ثم تنظم
                  الفريق والتنفيذ والجودة حتى التسليم.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  {["Requirement Analysis", "AI Planning", "Team", "QA", "Delivery"].map(
                    (item) => (
                      <span
                        key={item}
                        className="rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-[11px] text-white/50"
                      >
                        {item}
                      </span>
                    ),
                  )}
                </div>
              </a>
            </div>
          </div>
        </section>

        <section
          id="services"
          className="border-b border-white/[0.06] bg-[#050817] py-20"
        >
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:items-end">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300/80">
                  What We Build
                </div>
                <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                  حلول تقنية مبنية للتنفيذ الحقيقي.
                </h2>
                <p className="mt-4 text-sm leading-7 text-white/45 sm:text-base">
                  المنصة المستقبلية ستستخدم نفس الـoperating system لإدارة
                  دورة المشروع من تحليل الطلب وحتى التسليم.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {services.map((service) => (
                  <div
                    key={service}
                    className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5 text-sm font-medium text-white/70 backdrop-blur-xl transition hover:border-white/15 hover:bg-white/[0.04]"
                  >
                    {service}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-b border-white/[0.06] bg-[#07111d] py-20"
        >
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                How Kodraq Works
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                AI في المنتصف، والإنسان في القرار.
              </h2>
              <p className="mt-4 text-sm leading-7 text-white/45 sm:text-base">
                الـAI يحلل ويقترح ويساعد؛ والقرارات الحساسة تظل تحت
                إشراف بشري واضح.
              </p>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-4">
              {[
                ["01", "Understand", "فهم المتطلبات والسياق."],
                ["02", "Plan", "تقسيم العمل وتحديد الاحتياجات."],
                ["03", "Build", "تنفيذ منظم بمساعدة الـAI."],
                ["04", "Verify", "Review + QA + Delivery."],
              ].map(([number, title, description]) => (
                <div
                  key={number}
                  className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6"
                >
                  <div className="text-xs font-bold text-emerald-300/70">
                    {number}
                  </div>
                  <h3 className="mt-5 text-lg font-black">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-white/40">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/[0.06] bg-[#050817]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-xs text-white/35 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Kodraq Digital — Company Operating Platform</span>
          <span>Build. Learn. Automate.</span>
        </div>
      </footer>
    </div>
  );
}







