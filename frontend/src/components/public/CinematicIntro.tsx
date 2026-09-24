import { useEffect, useRef, useState } from "react";
import NeuralParticles from "./NeuralParticles";

const INTRO_STORAGE_KEY = "kodraq-public-intro-seen";

export default function CinematicIntro() {
  const startedRef = useRef(false);

  const [isVisible, setIsVisible] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    return !reducedMotion && sessionStorage.getItem(INTRO_STORAGE_KEY) !== "1";
  });

  useEffect(() => {
    if (!isVisible || startedRef.current) {
      return;
    }

    startedRef.current = true;

    const timeout = window.setTimeout(() => {
      sessionStorage.setItem(INTRO_STORAGE_KEY, "1");
      setIsVisible(false);
    }, 900);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [isVisible]);

  const skip = () => {
    sessionStorage.setItem(INTRO_STORAGE_KEY, "1");
    setIsVisible(false);
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[100] overflow-hidden bg-white text-slate-900"
      role="presentation"
    >
      <NeuralParticles particleCount={64} className="opacity-30" />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(91,155,213,0.12),transparent_30%),radial-gradient(circle_at_70%_30%,rgba(14,165,233,0.08),transparent_32%)]" />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-6">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-[28px] border border-blue-100 bg-blue-50 shadow-[0_0_70px_rgba(91,155,213,0.12)]">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5b9bd5] text-xl font-black text-white">
              KD
            </div>
          </div>

          <div className="text-[11px] font-semibold uppercase tracking-[0.55em] text-[#5b9bd5]">
            Kodraq Digital
          </div>

          <h1 className="mt-4 text-4xl font-black tracking-tight text-slate-900 sm:text-6xl">
            Build. Learn. Automate.
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-500 sm:text-base">
            A connected digital platform for learning, talent, software
            delivery, and AI-powered operations.
          </p>

          <div className="mx-auto mt-8 h-px w-40 overflow-hidden bg-slate-200">
            <div className="h-full w-1/2 animate-pulse bg-gradient-to-r from-[#5b9bd5] via-sky-400 to-transparent" />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={skip}
        className="absolute bottom-6 right-6 z-20 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-500 shadow-sm transition hover:bg-slate-50 hover:text-slate-900"
      >
        Skip
      </button>
    </div>
  );
}