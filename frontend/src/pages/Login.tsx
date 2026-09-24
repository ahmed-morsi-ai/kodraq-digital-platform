import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, LockKeyhole, X } from "lucide-react";
import { isAxiosError } from "axios";

import AuthToast from "@/components/AuthToast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return "Invalid email or password. Please try again.";
}

export default function Login() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState(
    searchParams.get("registered") === "1"
      ? "Account created successfully. Please sign in."
      : null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const clearRegisteredNotice = () => {
    setSuccessToast(null);

    if (searchParams.has("registered")) {
      const next = new URLSearchParams(searchParams);
      next.delete("registered");
      setSearchParams(next, { replace: true });
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorToast(null);
    setSuccessToast(null);
    setIsSubmitting(true);

    try {
      await login({ username: email.trim(), password });
      navigate("/dashboard");
    } catch (requestError: unknown) {
      console.error(
        "AUTH ERROR DETAILS:",
        isAxiosError(requestError)
          ? requestError.response?.data || requestError.message
          : requestError,
      );
      // Fixed: changed setError to setErrorToast
      setErrorToast(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-[#f8fbff] px-4 py-8 text-slate-900 sm:px-6">
      {successToast && (
        <AuthToast
          kind="success"
          message={successToast}
          onClose={clearRegisteredNotice}
        />
      )}

      {errorToast && (
        <AuthToast
          kind="error"
          message={errorToast}
          onClose={() => setErrorToast(null)}
        />
      )}

      <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center justify-center">
        <button
          type="button"
          aria-label="Close and return to home"
          onClick={handleClose}
          className="absolute right-0 top-0 inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="grid w-full max-w-4xl overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(91,155,213,0.12)] md:grid-cols-[0.85fr_1.15fr]">
          <div className="hidden bg-gradient-to-br from-[#edf6ff] via-white to-[#f7fbff] p-10 md:flex md:flex-col md:justify-between">
            <div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5b9bd5] text-sm font-black text-white shadow-lg shadow-blue-100">
                KD
              </div>
              <p className="mt-6 text-xs font-bold uppercase tracking-[0.28em] text-[#5b9bd5]">
                Kodraq Digital
              </p>
              <h1 className="mt-4 text-4xl font-black leading-tight text-slate-900">
                Build. Learn.
                <br />
                Automate.
              </h1>
              <p className="mt-5 max-w-sm text-sm leading-7 text-slate-500">
                Your learning workspace stays connected to the Kodraq digital
                platform.
              </p>
            </div>

            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-[#5b9bd5]"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
          </div>

          <div className="p-6 sm:p-8 md:p-10">
            <div className="mb-8 flex items-center gap-3 md:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#5b9bd5] text-xs font-black text-white">
                KD
              </div>
              <div>
                <p className="text-sm font-black text-slate-900">
                  Kodraq Digital
                </p>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
                  Learn. Build. Automate.
                </p>
              </div>
            </div>

            <div className="mb-8">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700">
                <LockKeyhole className="h-3.5 w-3.5" />
                Secure access
              </div>

              <h2 className="text-3xl font-black tracking-tight text-slate-900">
                Sign in
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Enter your Kodraq account details to continue.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  className="h-11 border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  className="h-11 border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                />
              </div>

              <Button
                type="submit"
                className="h-11 w-full bg-[#5b9bd5] font-bold text-white hover:bg-[#4a89c3]"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            <div className="mt-6 border-t border-slate-100 pt-6 text-center text-sm text-slate-500">
              New to Kodraq?{" "}
              <Link
                to="/register?persona=trainee"
                className="font-bold text-[#5b9bd5] hover:underline"
              >
                Create an account
              </Link>
            </div>

            <Link
              to="/"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}