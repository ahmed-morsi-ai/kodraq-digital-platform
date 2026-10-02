import { useEffect, useRef, useState } from "react";
import { Brain, ArrowLeft, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

const PROMO_STORAGE_KEY = "hasSeenPromo";

function shouldShowPromo() {
  if (typeof window === "undefined") return false;

  try {
    return window.sessionStorage.getItem(PROMO_STORAGE_KEY) !== "1";
  } catch {
    return true;
  }
}

export default function WelcomePromo() {
  const navigate = useNavigate();
  const brainMotionRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(shouldShowPromo);
  const [phase, setPhase] = useState<"splash" | "transition" | "promo">("splash");

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    try {
      window.sessionStorage.setItem(PROMO_STORAGE_KEY, "1");
    } catch {
      // Continue showing the promo when session storage is unavailable.
    }

    const transitionTimer = window.setTimeout(() => setPhase("transition"), 1500);
    const splashTimer = window.setTimeout(() => setPhase("promo"), 2000);

    return () => {
      window.clearTimeout(transitionTimer);
      window.clearTimeout(splashTimer);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    const brain = brainMotionRef.current;
    if (!isOpen || !brain || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const animation = brain.animate(
      [
        { transform: "rotateY(-15deg) rotateX(10deg) scale(1.05) translateY(0)" },
        { transform: "rotateY(15deg) rotateX(10deg) scale(1.05) translateY(-10px)" },
        { transform: "rotateY(-15deg) rotateX(10deg) scale(1.05) translateY(0)" },
      ],
      { duration: 3600, iterations: Number.POSITIVE_INFINITY, easing: "ease-in-out" },
    );

    return () => animation.cancel();
  }, [isOpen]);

  const closePromo = () => setIsOpen(false);

  if (!isOpen) return null;

  const isSplashVisible = phase === "splash";
  const isPromoVisible = phase !== "splash";

  return (
    <div dir="rtl" className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-4">
      <div
        aria-hidden="true"
        className={`absolute inset-0 transition-colors duration-500 ${isPromoVisible ? "bg-[#0B1120]/75 backdrop-blur-sm" : "bg-[#0B1120]"}`}
      />
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0 transition-opacity duration-500 ${isSplashVisible ? "opacity-100" : "opacity-0"}`}
        style={{
          backgroundImage:
            "linear-gradient(rgba(37,99,235,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(37,99,235,0.07) 1px, transparent 1px), radial-gradient(ellipse at center, rgba(6,182,212,0.12), transparent 58%)",
          backgroundSize: "44px 44px, 44px 44px, auto",
        }}
      />

      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0 z-10 flex items-center justify-center transition-opacity duration-500 ${isSplashVisible ? "opacity-100" : "opacity-0"}`}
      >
        <div className="relative flex size-72 items-center justify-center [perspective:1000px]">
          <div className="absolute h-40 w-64 rounded-[50%] border border-blue-500/40 shadow-[0_0_24px_rgba(37,99,235,0.35)] [transform:rotateX(68deg)]" />
          <div className="absolute h-52 w-40 rounded-[50%] border border-cyan-400/25 [transform:rotateY(68deg)]" />
          <div ref={brainMotionRef} className="relative [transform-style:preserve-3d]">
            <Brain
              aria-hidden="true"
              className="absolute left-0 top-0 size-[120px] -translate-x-1.5 text-blue-500 opacity-55"
              strokeWidth={1.35}
              style={{ filter: "drop-shadow(0 0 12px rgba(37,99,235,0.9))" }}
            />
            <Brain
              aria-hidden="true"
              className="relative size-[120px] animate-pulse text-cyan-200"
              strokeWidth={1.35}
              style={{
                filter:
                  "drop-shadow(0 0 5px rgba(37,99,235,1)) drop-shadow(0 0 16px rgba(6,182,212,0.95)) drop-shadow(8px 16px 22px rgba(37,99,235,0.55))",
              }}
            />
            {/* <img src="/3d-tech-brain.gif" alt="3D Brain" className="size-[120px] object-contain" /> */}
          </div>
        </div>
      </div>

      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="welcome-promo-title"
        className={`relative z-20 my-auto w-full max-w-xl rounded-xl border border-blue-100 bg-white p-6 text-slate-900 shadow-[0_24px_80px_rgba(11,17,32,0.35)] transition-all duration-500 ease-out sm:p-8 ${isPromoVisible ? "scale-100 opacity-100" : "pointer-events-none scale-95 opacity-0"}`}
      >
        <button
          type="button"
          aria-label="إغلاق"
          onClick={closePromo}
          className="absolute right-4 top-4 inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <X aria-hidden="true" className="size-4" />
        </button>

        <h2 id="welcome-promo-title" className="pl-10 text-xl font-extrabold leading-8 text-slate-900 sm:text-2xl">
          🚀 انضم لنخبة المهندسين في Kodraq
        </h2>
        <p className="mt-5 text-sm leading-7 text-slate-600 sm:text-base">
          طريقك لا يبدأ وينتهي عند مجرد دورة تدريبية! نحن لا ندربك فقط، بل نتبنى المتميزين. أبرز العقول التي تخرجت من مساراتنا انضموا بالفعل لـ Kodraq Talent Pool، وهم الآن يعملون معنا جنباً إلى جنب كمهندسين في بناء وتطوير مشاريع وأنظمة حقيقية للسوق.
        </p>

        <p className="mt-5 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-bold leading-6 text-blue-800 sm:text-base">
          💡 كن أنت المهندس القادم في فريقنا.
        </p>

        <button
          type="button"
          onClick={() => {
            closePromo();
            navigate("/tracks");
          }}
          className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-5 py-3 text-sm font-extrabold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        >
          تصفح المسارات وابدأ رحلتك
          <ArrowLeft aria-hidden="true" className="size-4" />
        </button>
      </section>
    </div>
  );
}