import { ArrowUpRight, BrainCircuit, BriefcaseBusiness, ChevronDown, Code2, Layers3, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import CinematicIntro from "@/components/public/CinematicIntro";
import NeuralParticles from "@/components/public/NeuralParticles";

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

      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#050817]/55 backdrop-blur-2xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/10 text-sm font-black text-emerald-300 shadow-[0_0_28px_rgba(16,185,129,0.12)]">
              KD
            </div>

            <div>
              <div className="text-sm font-black tracking-tight">Kodraq Digital</div>
              <div className="text-[10px] uppercase tracking-[0.32em] text-white/35">
                Learn. Build. Automate.
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm text-white/55 md:flex">
            <a className="transition hover:text-white" href="#home">
              الرئيسية
            </a>
            <a className="transition hover:text-white" href="#paths">
              المسارات
            </a>
            <a className="transition hover:text-white" href="#services">
              الخدمات
            </a>
            <a className="transition hover:text-white" href="#how-it-works">
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
        <section
          id="home"
          className="relative isolate flex min-h-screen items-center overflow-hidden pt-20"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.12),transparent_28%),radial-gradient(circle_at_80%_25%,rgba(34,211,238,0.10),transparent_30%),linear-gradient(180deg,#050817_0%,#07111c_100%)]" />

          <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] [background-size:64px_64px]" />

          <div className="absolute inset-y-0 left-0 w-1/2 opacity-90">
            <NeuralParticles particleCount={92} />
          </div>

          <div className="relative z-10 mx-auto grid w-full max-w-7xl gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-300/[0.06] px-3 py-1.5 text-[11px] font-semibold text-emerald-200/90 backdrop-blur-xl">
                <Sparkles className="h-3.5 w-3.5" />
                شركة تقنية يقودها الذكاء الاصطناعي
              </div>

              <h1 className="mt-7 text-5xl font-black leading-[1.05] tracking-[-0.04em] sm:text-6xl lg:text-7xl">
                نبني
                <span className="bg-gradient-to-r from-emerald-300 via-cyan-300 to-sky-300 bg-clip-text text-transparent">
                  {" "}
                  المواهب
                </span>
                <br />
                ونبني
                <span className="bg-gradient-to-r from-cyan-300 via-emerald-300 to-white bg-clip-text text-transparent">
                  {" "}
                  المنتجات
                </span>
                .
              </h1>

              <p className="mt-7 max-w-2xl text-base leading-8 text-white/58 sm:text-lg">
                Kodraq Digital تجمع التدريب المكثف، الذكاء الاصطناعي، تطوير
                البرمجيات، وإدارة المشاريع داخل منظومة واحدة تساعد الأشخاص على
                التعلم وتساعد الشركات على بناء حلول تقنية حقيقية.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <a
                  href="#paths"
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-300 to-cyan-300 px-6 py-3.5 text-sm font-black text-slate-950 shadow-[0_14px_50px_rgba(16,185,129,0.18)] transition hover:-translate-y-0.5"
                >
                  اكتشف مسارك
                  <ArrowUpRight className="h-4 w-4" />
                </a>

                <a
                  href="#services"
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-white/85 backdrop-blur-xl transition hover:bg-white/[0.08]"
                >
                  استكشف خدمات Kodraq
                  <Layers3 className="h-4 w-4" />
                </a>
              </div>

              <div className="mt-10 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ["AI", "في قلب المنصة"],
                  ["20+", "مسارات تقنية"],
                  ["1", "منظومة موحدة"],
                  ["GCC", "السوق المستهدف"],
                ].map(([value, label]) => (
                  <div
                    key={value}
                    className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 backdrop-blur-xl"
                  >
                    <div className="text-xl font-black text-white">{value}</div>
                    <div className="mt-1 text-[11px] text-white/40">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl">
              <div className="absolute -inset-10 rounded-full bg-emerald-300/[0.07] blur-3xl" />

              <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-white/[0.035] p-4 shadow-[0_40px_120px_rgba(0,0,0,0.45)] backdrop-blur-2xl">
                <div className="relative aspect-square overflow-hidden rounded-[26px] border border-white/[0.07] bg-[#07111d]">
                  <NeuralParticles particleCount={110} />

                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_46%,rgba(16,185,129,0.18),transparent_24%),radial-gradient(circle_at_55%_58%,rgba(34,211,238,0.08),transparent_38%)]" />

                  <div className="absolute left-1/2 top-1/2 flex h-44 w-44 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-emerald-300/15 bg-emerald-300/[0.03] shadow-[0_0_120px_rgba(16,185,129,0.16)]">
                    <div className="flex h-28 w-28 items-center justify-center rounded-full border border-cyan-300/15 bg-cyan-300/[0.04]">
                      <BrainCircuit className="h-14 w-14 text-emerald-200/80" strokeWidth={1.2} />
                    </div>
                  </div>

                  <div className="absolute bottom-4 left-4 right-4 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-white/[0.07] bg-black/25 p-4 backdrop-blur-xl">
                      <div className="flex items-center gap-2 text-xs font-semibold text-emerald-200">
                        <Code2 className="h-4 w-4" />
                        Kodraq Academy
                      </div>
                      <p className="mt-2 text-xs leading-5 text-white/45">
                        Learn with dedicated AI guidance, practical tasks and real projects.
                      </p>
                    </div>

                    <div className="rounded-2xl border border-white/[0.07] bg-black/25 p-4 backdrop-blur-xl">
                      <div className="flex items-center gap-2 text-xs font-semibold text-cyan-200">
                        <BriefcaseBusiness className="h-4 w-4" />
                        Kodraq Services
                      </div>
                      <p className="mt-2 text-xs leading-5 text-white/45">
                        Turn business requirements into structured, production-ready delivery.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between px-2 text-[11px] text-white/35">
                <span>AI-powered company operating platform</span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.8)]" />
                  Live concept
                </span>
              </div>
            </div>
          </div>

          <a
            href="#paths"
            className="absolute bottom-7 left-1/2 z-20 -translate-x-1/2 text-white/30 transition hover:text-white/70"
            aria-label="Scroll to pathways"
          >
            <ChevronDown className="h-6 w-6 animate-bounce" />
          </a>
        </section>

        <section
          id="paths"
          className="relative border-y border-white/[0.06] bg-[#07111d] py-20"
        >
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                Choose your path
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                مساران، ومنظومة واحدة.
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
                  What we build
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
                How Kodraq works
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                AI في المنتصف، والإنسان في القرار.
              </h2>
              <p className="mt-4 text-sm leading-7 text-white/45 sm:text-base">
                الذكاء الاصطناعي يحلل ويقترح ويساعد؛ والقرارات الحساسة تظل تحت
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



