
$ErrorActionPreference = "Stop"

$repo = (Get-Location).Path

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText(
        (Resolve-Path $Path),
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Write-NewUtf8NoBom([string]$Path, [string]$Content) {
    $full = Join-Path $repo $Path
    $dir = Split-Path $full -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText(
        $full,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host "TASK-UI-POLISH audit/apply starting..." -ForegroundColor Cyan

# 1) Global light theme + disable OS-driven dark variant.
Write-NewUtf8NoBom ".\frontend\src\index.css" @'
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}

@layer base {
  html {
    color-scheme: light;
    background: #f8fbff;
  }

  body {
    @apply min-h-full bg-[#f8fbff] text-slate-900 antialiased;
  }

  #root {
    @apply min-h-screen;
  }

  ::selection {
    background: #dbeafe;
    color: #0f172a;
  }
}
'@

# 2) Shared auth toast.
Write-NewUtf8NoBom ".\frontend\src\components\AuthToast.tsx" @'
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
'@

# 3) Auth type for registration.
$authTypesPath = ".\frontend\src\types\auth.ts"
$authTypes = Get-Content $authTypesPath -Raw
if ($authTypes -notmatch "RegisterCredentials") {
    $authTypes = $authTypes.Replace(
@'
export interface TokenResponse {
  access_token: string;
  token_type: string;
}
'@,
@'
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterCredentials {
  email: string;
  full_name: string;
  password: string;
}
'@
    )
    Write-Utf8NoBom $authTypesPath $authTypes
}

# 4) Registration API. Backend's public equivalent is POST /api/v1/users.
$authServicePath = ".\frontend\src\services\auth.service.ts"
$authService = Get-Content $authServicePath -Raw
if ($authService -notmatch "async register") {
    $authService = $authService.Replace(
'import type { User, LoginCredentials, TokenResponse } from "../types/auth";',
'import type { RegisterCredentials, User, LoginCredentials, TokenResponse } from "../types/auth";'
    )
    $authService = $authService.Replace(
@'
  async getCurrentUser(): Promise<User> {
'@,
@'
  async register(credentials: RegisterCredentials): Promise<User> {
    const response = await api.post<User>("/api/v1/users", credentials);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
'@
    )
    Write-Utf8NoBom $authServicePath $authService
}

# 5) Light login page with close/back controls and sign-up toggle.
Write-NewUtf8NoBom ".\frontend\src\pages\Login.tsx" @'
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, LockKeyhole, X } from "lucide-react";
import { isAxiosError } from "axios";

import AuthToast from "@/components/AuthToast";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
    } catch (requestError) {
      console.error("Login failed", requestError);
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
'@

# 6) Registration page.
Write-NewUtf8NoBom ".\frontend\src\pages\Register.tsx" @'
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, UserRound, X } from "lucide-react";
import { isAxiosError } from "axios";

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
      console.error("Registration failed", requestError);
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
'@

# 7) Add /register route without touching the rest of App.tsx.
$appPath = ".\frontend\src\App.tsx"
$app = Get-Content $appPath -Raw
if ($app -notmatch 'import Register from "\./pages/Register";') {
    $app = $app.Replace(
'import Login from "./pages/Login";',
'import Login from "./pages/Login";' + [Environment]::NewLine + 'import Register from "./pages/Register";'
    )
}
if ($app -notmatch 'path="/register"') {
    $app = $app.Replace(
'<Route path="/login" element={<Login />} />',
'<Route path="/login" element={<Login />} />' + [Environment]::NewLine + '        <Route path="/register" element={<Register />} />'
    )
}
Write-Utf8NoBom $appPath $app

# 8) Harmonize protected layout, preserving the Payments navigation already added.
Write-NewUtf8NoBom ".\frontend\src\layouts\RootLayout.tsx" @'
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function RootLayout() {
  const location = useLocation();
  const { user } = useAuth();

  const navigation = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Tracks", href: "/tracks" },
    { label: "My Learning", href: "/my-learning" },
    { label: "Certificates", href: "/certificates" },
    ...(user?.is_superuser || user?.role === "admin"
      ? [{ label: "Payments", href: "/admin/payments" }]
      : []),
  ];

  return (
    <div className="min-h-screen bg-[#f8fbff] text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-6 px-5 sm:px-8">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#5b9bd5] text-xs font-black text-white shadow-sm shadow-blue-100">
              KD
            </div>
            <div>
              <div className="text-sm font-black tracking-tight text-slate-900">
                Kodraq Digital
              </div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">
                Learn. Build. Automate.
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {navigation.map((item) => {
              const isActive =
                location.pathname === item.href ||
                (item.href !== "/dashboard" &&
                  location.pathname.startsWith(`${item.href}/`));

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`rounded-full px-4 py-2 text-xs font-semibold transition ${
                    isActive
                      ? "bg-blue-50 text-[#4a89c3]"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <Link
            to="/"
            className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:inline-flex"
          >
            Home
          </Link>
        </div>
      </header>

      <main className="min-h-[calc(100vh-64px)]">
        <Outlet />
      </main>
    </div>
  );
}
'@

# 9) Harmonize public landing sections to the same light brand.
Write-NewUtf8NoBom ".\frontend\src\pages\Landing.tsx" @'
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
      className="min-h-screen overflow-x-hidden bg-[#f8fbff] text-slate-900"
    >
      <CinematicIntro />

      <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#5b9bd5] text-sm font-black text-white shadow-lg shadow-blue-100">
              KD
            </div>

            <div>
              <div className="text-sm font-black tracking-tight text-slate-900">
                Kodraq Digital
              </div>
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
              className="hidden rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:inline-flex"
            >
              دخول
            </Link>

            <Link
              to="/register?persona=trainee"
              className="inline-flex items-center gap-2 rounded-full bg-[#5b9bd5] px-4 py-2 text-xs font-black text-white shadow-lg shadow-blue-100 transition hover:-translate-y-0.5 hover:bg-[#4a89c3]"
            >
              ابدأ الآن
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <main id="home">
        <PublicLandingHero />

        <section id="paths" className="border-y border-slate-200 bg-white py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#5b9bd5]">
                Choose Your Path
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                مساران. One Platform.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                سواء كنت تبني مستقبلك التقني أو تبني منتجًا لشركتك، Kodraq
                مصممة لتأخذك من المتطلبات إلى نتيجة حقيقية.
              </p>
            </div>

            <div className="mt-10 grid gap-5 lg:grid-cols-2">
              <Link
                to="/register?persona=trainee"
                className="group rounded-[28px] border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-7 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-100/60"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-100 text-[#5b9bd5]">
                    <Code2 className="h-6 w-6" />
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-slate-300 transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-[#5b9bd5]" />
                </div>

                <h3 className="mt-7 text-2xl font-black text-slate-900">
                  أنا متدرب
                </h3>

                <p className="mt-3 max-w-xl text-sm leading-7 text-slate-500">
                  اختر تخصصك، تعلّم بشكل مكثف، استخدم الـAI Tutor، نفّذ المهام،
                  وابنِ مشروعًا حقيقيًا يثبت قدراتك.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  {["Tracks", "AI Tutor", "Tasks", "Projects", "Certification"].map(
                    (item) => (
                      <span
                        key={item}
                        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-500"
                      >
                        {item}
                      </span>
                    ),
                  )}
                </div>
              </Link>

              <a
                href="#services"
                className="group rounded-[28px] border border-slate-200 bg-gradient-to-br from-sky-50 to-white p-7 shadow-sm transition hover:-translate-y-1 hover:border-sky-200 hover:shadow-xl hover:shadow-sky-100/60"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-600">
                    <BriefcaseBusiness className="h-6 w-6" />
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-slate-300 transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-sky-600" />
                </div>

                <h3 className="mt-7 text-2xl font-black text-slate-900">
                  أنا عميل
                </h3>

                <p className="mt-3 max-w-xl text-sm leading-7 text-slate-500">
                  اشرح فكرتك، دع Kodraq تفهم المتطلبات، تبني الـscope، ثم تنظم
                  الفريق والتنفيذ والجودة حتى التسليم.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  {["Requirement Analysis", "AI Planning", "Team", "QA", "Delivery"].map(
                    (item) => (
                      <span
                        key={item}
                        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-500"
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

        <section id="services" className="border-b border-slate-200 bg-[#f8fbff] py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:items-end">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#5b9bd5]">
                  What We Build
                </div>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                  حلول تقنية مبنية للتنفيذ الحقيقي.
                </h2>
                <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                  المنصة المستقبلية ستستخدم نفس الـoperating system لإدارة دورة
                  المشروع من تحليل الطلب وحتى التسليم.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {services.map((service) => (
                  <div
                    key={service}
                    className="rounded-2xl border border-slate-200 bg-white p-5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-blue-200 hover:bg-blue-50/40"
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
          className="border-b border-slate-200 bg-white py-20"
        >
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="max-w-2xl">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#5b9bd5]">
                How Kodraq Works
              </div>
              <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                AI في المنتصف، والإنسان في القرار.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                الـAI يحلل ويقترح ويساعد؛ والقرارات الحساسة تظل تحت إشراف بشري
                واضح.
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
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-6"
                >
                  <div className="text-xs font-bold text-[#5b9bd5]">{number}</div>
                  <h3 className="mt-5 text-lg font-black text-slate-900">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-[#f8fbff]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Kodraq Digital — Company Operating Platform</span>
          <span>Build. Learn. Automate.</span>
        </div>
      </footer>
    </div>
  );
}
'@

# 10) Make the intro match the light brand instead of introducing a dark splash.
Write-NewUtf8NoBom ".\frontend\src\components\public\CinematicIntro.tsx" @'
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
'@

Write-Host ""
Write-Host "TASK-UI-POLISH apply complete." -ForegroundColor Green
Write-Host "No git commands were executed." -ForegroundColor Yellow
