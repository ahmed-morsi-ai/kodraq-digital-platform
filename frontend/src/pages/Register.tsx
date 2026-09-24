import { isAxiosError } from "axios";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, UserRound, X } from "lucide-react";

import AuthToast from "@/components/AuthToast";
import { AuthService } from "@/services/auth.service";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) =>
          typeof item === "string" ? item : item?.msg ?? "Invalid input",
        )
        .join(" ");
    }

    if (error.response?.status === 409) {
      return "An account with this email already exists.";
    }
  }

  return "Registration failed. Please check your information and try again.";
}

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorToast(null);
    setSuccessToast(null);

    if (password.length < 8) {
      setErrorToast("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorToast("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      await AuthService.register({
        email: email.trim(),
        full_name: fullName.trim(),
        password,
      });

      setSuccessToast(
        "Account created successfully. Redirecting you to sign in...",
      );

      window.setTimeout(() => {
        navigate("/login?registered=1", { replace: true });
      }, 900);
    } catch (requestError) {
      if (isAxiosError(requestError)) {
        console.error(
          "AUTH ERROR DETAILS:",
          requestError.response?.data ?? requestError.message,
        );
      } else {
        console.error("AUTH ERROR DETAILS:", requestError);
      }
      
      // التعديل هنا: إضافة سطر عرض الخطأ للمستخدم
      setErrorToast(getErrorMessage(requestError));
      
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fbff] px-4 py-8 text-slate-900 sm:px-6">
      {successToast && (
        <AuthToast
          kind="success"
          message={successToast}
          onClose={() => setSuccessToast(null)}
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
          onClick={() => navigate("/")}
          className="absolute right-0 top-0 inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
        >
          <X className="h-5 w-5" />
        </button>

        <Card className="w-full max-w-xl border-slate-200 bg-white shadow-[0_24px_80px_rgba(91,155,213,0.12)]">
          <CardHeader className="p-6 sm:p-8">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5b9bd5] text-sm font-black text-white shadow-lg shadow-blue-100">
                KD
              </div>
              <div>
                <p className="text-sm font-black text-slate-900">
                  Kodraq Digital
                </p>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
                  Kodraq Academy
                </p>
              </div>
            </div>

            <div className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700">
              <UserRound className="h-3.5 w-3.5" />
              New trainee account
            </div>

            <CardTitle className="mt-4 text-3xl font-black tracking-tight text-slate-900">
              Create your account
            </CardTitle>
            <CardDescription className="mt-2 leading-6 text-slate-500">
              Register once, then use the same account for tracks, payments,
              projects, and certification.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-6 pt-0 sm:p-8 sm:pt-0">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  type="text"
                  autoComplete="name"
                  placeholder="Ahmed Morsi"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                  className="h-11 border-slate-200 bg-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="register_email">Email address</Label>
                <Input
                  id="register_email"
                  type="email"
                  autoComplete="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  className="h-11 border-slate-200 bg-white"
                />
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="register_password">Password</Label>
                  <Input
                    id="register_password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={8}
                    className="h-11 border-slate-200 bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm_password">Confirm password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Repeat password"
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    required
                    minLength={8}
                    className="h-11 border-slate-200 bg-white"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="h-11 w-full bg-[#5b9bd5] font-bold text-white hover:bg-[#4a89c3]"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Creating account..." : "Create account"}
              </Button>
            </form>

            <div className="mt-6 border-t border-slate-100 pt-6 text-center text-sm text-slate-500">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-bold text-[#5b9bd5] hover:underline"
              >
                Sign in
              </Link>
            </div>

            <Link
              to="/"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}