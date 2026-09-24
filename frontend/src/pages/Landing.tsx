import { ArrowUpRight } from "lucide-react";
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
    <div dir="rtl" className="min-h-screen overflow-x-hidden bg-white text-slate-900">
      <CinematicIntro />

      <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-6 px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#5B9BD5] text-sm font-black text-white shadow-sm">
              KD
            </div>
            <div>
              <div className="text-sm font-black tracking-tight text-slate-900">Kodraq Digital</div>
              <div className="text-[10px] uppercase tracking-[0.32em] text-slate-400">Learn. Build. Automate.</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm text-slate-500 md:flex">
            <a className="transition hover:text-slate-900" href="#home">الرئيسية</a>
            <a className="transition hover:text-slate-900" href="#services">الخدمات</a>
            <a className="transition hover:text-slate-900" href="#how-it-works">كيف نعمل</a>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/login?persona=trainee"
              className="hidden rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:border-[#BFDFFF] hover:text-slate-900 sm:inline-flex"
            >
              دخول
            </Link>
            <Link
              to="/register?persona=trainee"
              className="inline-flex items-center gap-2 rounded-full bg-[#5B9BD5] px-4 py-2 text-xs font-black text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-[#4D8DC7]"
            >
              ابدأ الآن
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <PublicLandingHero />

        <section id="services" className="border-y border-slate-200 bg-[#F7FBFF] py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:items-end">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#5B9BD5]">What We Build</div>
                <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">حلول تقنية مبنية للتنفيذ الحقيقي</h2>
                <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                  المنصة المستقبلية ستستخدم نفس الـoperating system لإدارة دورة المشروع من تحليل الطلب وحتى التسليم.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {services.map((service) => (
                  <div key={service} className="rounded-2xl border border-slate-200 bg-white p-5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-[#BFDFFF] hover:shadow-md">
                    {service}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-b border-slate-200 bg-white py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#5B9BD5]">How Kodraq Works</div>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">AI في المنتصف، والإنسان في القرار.</h2>
              <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                الـAI يحلل ويقترح ويساعد؛ والقرارات الحساسة تظل تحت إشراف بشري واضح.
              </p>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-4">
              {[
                ["01", "Understand", "فهم المتطلبات والسياق."],
                ["02", "Plan", "تقسيم العمل وتحديد الاحتياجات."],
                ["03", "Build", "تنفيذ منظم بمساعدة الـAI."],
                ["04", "Verify", "Review + QA + Delivery."],
              ].map(([number, title, description]) => (
                <div key={number} className="rounded-2xl border border-slate-200 bg-[#F8FBFE] p-6 shadow-sm">
                  <div className="text-xs font-bold text-[#5B9BD5]">{number}</div>
                  <h3 className="mt-5 text-lg font-black text-slate-900">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Kodraq Digital — Company Operating Platform</span>
          <span>Build. Learn. Automate.</span>
        </div>
      </footer>
    </div>
  );
}