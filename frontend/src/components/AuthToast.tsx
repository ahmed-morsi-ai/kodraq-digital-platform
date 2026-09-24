import { AlertCircle, CheckCircle2, X } from "lucide-react";

interface AuthToastProps {
  kind: "success" | "error";
  message: string;
  onClose: () => void;
}

export default function AuthToast({
  kind,
  message,
  onClose,
}: AuthToastProps) {
  const isSuccess = kind === "success";

  return (
    <div
      role={isSuccess ? "status" : "alert"}
      className={`fixed right-4 top-4 z-[100] flex w-[min(92vw,420px)] items-start gap-3 rounded-2xl border bg-white p-4 shadow-xl ${
        isSuccess
          ? "border-emerald-200 text-emerald-800"
          : "border-red-200 text-red-800"
      }`}
    >
      {isSuccess ? (
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
      ) : (
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
      )}

      <p className="min-w-0 flex-1 text-sm font-medium leading-6">
        {message}
      </p>

      <button
        type="button"
        aria-label="Close notification"
        onClick={onClose}
        className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}