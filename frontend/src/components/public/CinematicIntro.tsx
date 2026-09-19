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
    }, 1100);

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
      className="fixed inset-0 z-[100] overflow-hidden bg-[#050817] text-white"
      role="presentation"
    >
      <NeuralParticles particleCount={86} />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(16,185,129,0.18),transparent_28%),radial-gradient(circle_at_70%_30%,rgba(34,211,238,0.12),transparent_30%)]" />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-6">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-[28px] border border-white/10 bg-white/[0.05] shadow-[0_0_80px_rgba(16,185,129,0.12)] backdrop-blur-xl">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-xl font-black text-emerald-300">
              KD
            </div>
          </div>

          <div className="text-[11px] font-semibold uppercase tracking-[0.55em] text-emerald-300/80">
            Kodraq Digital
          </div>

          <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-6xl">
            Build. Learn. Automate.
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-white/60 sm:text-base">
            A connected digital platform for learning, talent, software
            delivery, and AI-powered operations.
          </p>

          <div className="mx-auto mt-8 h-px w-40 overflow-hidden bg-white/10">
            <div className="h-full w-1/2 animate-pulse bg-gradient-to-r from-emerald-300 via-cyan-300 to-transparent" />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={skip}
        className="absolute bottom-6 right-6 z-20 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-medium text-white/55 backdrop-blur-xl transition hover:bg-white/[0.08] hover:text-white"
      >
        Skip
      </button>
    </div>
  );
}
