$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$frontend = Join-Path $root 'frontend'
$src = Join-Path $frontend 'src'

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText(
        (Resolve-Path $Path),
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Assert-File([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "Required file not found: $Path"
    }
}

Write-Host "TASK-BUG-SQUASH manual override starting..." -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1) index.html — explicit UTF-8 + Arabic document direction
# -----------------------------------------------------------------------------
$indexPath = Join-Path $frontend 'index.html'
Assert-File $indexPath
$index = Get-Content $indexPath -Raw
$index = [regex]::Replace($index, '(?is)<meta\s+charset\s*=\s*["''][^"'']*["'']\s*/?>', '<meta charset="UTF-8" />', 1)
if ($index -notmatch '<meta\s+charset\s*=\s*["'']UTF-8["'']') {
    $index = $index -replace '(?i)(<head[^>]*>)', '$1' + "`r`n    <meta charset=`"UTF-8`" />"
}
$index = $index -replace '<html\s+lang="[^"]*"', '<html lang="ar"'
Write-Utf8NoBom $indexPath $index

# -----------------------------------------------------------------------------
# 2) PublicLandingHero.tsx — rewrite Arabic strings and keep ONE persona pair
# -----------------------------------------------------------------------------
$heroPath = Join-Path $src 'components\public\PublicLandingHero.tsx'
Assert-File $heroPath
$hero = @'
import { ArrowLeft, Briefcase, GraduationCap } from "lucide-react";
import { Link } from "react-router-dom";

export default function PublicLandingHero() {
  return (
    <section
      id="home"
      dir="rtl"
      className="relative min-h-screen overflow-hidden bg-white px-6 pb-20 pt-28 text-slate-900 md:px-12"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
        <div className="absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl">
        <div className="mx-auto mb-16 max-w-4xl text-center">
          <div className="mb-5 text-xs font-bold uppercase tracking-[0.3em] text-[#5B9BD5]">
            Kodraq Digital
          </div>

          <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 md:text-6xl">
            مستقبلك الرقمي يبدأ مع <span className="text-[#5B9BD5]">Kodraq</span>
          </h1>

          <p className="mx-auto max-w-3xl text-lg font-medium leading-relaxed text-slate-500 md:text-xl">
            سواء كنت تطمح لبناء مسيرتك في التقنية أو تبحث عن حلول برمجية ترتقي بأعمالك، Kodraq تساعدك على الانتقال من الفكرة إلى نتيجة حقيقية.
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-2">
          <Link
            to="/register?persona=trainee"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-[#BFDFFF] hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <GraduationCap size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا متدرب
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Academy
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                ابدأ رحلتك مع برامج تدريبية مكثفة في Technical Tracks حقيقية، وتعلّم من خلال Practical Tasks وProjects تساعدك على بناء مهاراتك والاستعداد لسوق العمل.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>ابدأ رحلتك التعليمية</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </Link>

          <Link
            to="/login?persona=client"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-[#BFDFFF] hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <Briefcase size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا عميل
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Services
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                حوّل فكرتك إلى Digital Product قابل للتوسع من خلال Web & Software Development وAI Automation وUI/UX وCloud Solutions مصممة باحتياجات عملك.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>اكتشف Kodraq Services</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </Link>
        </div>
      </div>
    </section>
  );
}
'@
Write-Utf8NoBom $heroPath $hero

# -----------------------------------------------------------------------------
# 3) Landing.tsx — rewrite shell/sections with clean light theme and no duplicate
#    persona cards. Persona choices exist only in PublicLandingHero.tsx above.
# -----------------------------------------------------------------------------
$landingPath = Join-Path $src 'pages\Landing.tsx'
Assert-File $landingPath
$landing = @'
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
'@
Write-Utf8NoBom $landingPath $landing

# -----------------------------------------------------------------------------
# 4) auth.service.ts — exact FastAPI OAuth2 login + UserCreate registration
# -----------------------------------------------------------------------------
$authServicePath = Join-Path $src 'services\auth.service.ts'
Assert-File $authServicePath
$authService = @'
import { api } from "./api";
import type {
  LoginCredentials,
  RegistrationPayload,
  TokenResponse,
  User,
} from "@/types/auth";

export const AuthService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    try {
      const formData = new URLSearchParams();
      formData.set("grant_type", "password");
      formData.set("username", credentials.username.trim());
      formData.set("password", credentials.password);

      const response = await api.post<TokenResponse>(
        "/api/v1/login/access-token",
        formData,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        },
      );

      return response.data;
    } catch (error: unknown) {
      const details = error as { response?: { data?: unknown }; message?: string };
      console.error("AUTH ERROR DETAILS:", details.response?.data || details.message || error);
      throw error;
    }
  },

  async register(payload: RegistrationPayload): Promise<User> {
    try {
      const response = await api.post<User>("/api/v1/users", {
        email: payload.email.trim(),
        full_name: payload.full_name.trim(),
        password: payload.password,
      });

      return response.data;
    } catch (error: unknown) {
      const details = error as { response?: { data?: unknown }; message?: string };
      console.error("AUTH ERROR DETAILS:", details.response?.data || details.message || error);
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/users/me");
    return response.data;
  },
};
'@
Write-Utf8NoBom $authServicePath $authService

# -----------------------------------------------------------------------------
# 5) auth.ts — explicit registration payload contract
# -----------------------------------------------------------------------------
$authTypesPath = Join-Path $src 'types\auth.ts'
Assert-File $authTypesPath
$authTypes = @'
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  role?: string | null;
  role_name: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegistrationPayload {
  email: string;
  full_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
'@
Write-Utf8NoBom $authTypesPath $authTypes

# -----------------------------------------------------------------------------
# 6) Login.tsx — retain current visual intent, guarantee browser-side backend log
# -----------------------------------------------------------------------------
$loginPath = Join-Path $src 'pages\Login.tsx'
Assert-File $loginPath
$login = Get-Content $loginPath -Raw
if ($login -notmatch 'AUTH ERROR DETAILS:') {
    $newline = [Environment]::NewLine
    $logReplacement = 'catch ($1) {' + $newline + '      console.error("AUTH ERROR DETAILS:", $1?.response?.data || $1?.message || $1);'
    $login = [regex]::Replace(
        $login,
        'catch\s*\(([^)]*)\)\s*\{',
        $logReplacement,
        1
    )
}
Write-Utf8NoBom $loginPath $login

# -----------------------------------------------------------------------------
# 7) Register.tsx — guarantee exact UserCreate payload and browser-side logging.
#    The existing form/UI is preserved; only the service call is normalized.
# -----------------------------------------------------------------------------
$registerPath = Join-Path $src 'pages\Register.tsx'
Assert-File $registerPath
$register = Get-Content $registerPath -Raw


if ($register -notmatch 'AUTH ERROR DETAILS:') {
    $newline = [Environment]::NewLine
    $logReplacement = 'catch ($1) {' + $newline + '      console.error("AUTH ERROR DETAILS:", $1?.response?.data || $1?.message || $1);'
    $register = [regex]::Replace(
        $register,
        'catch\s*\(([^)]*)\)\s*\{',
        $logReplacement,
        1
    )
}

Write-Utf8NoBom $registerPath $register

Write-Host "" 
Write-Host "MANUAL OVERRIDE APPLIED TO LOCAL WORKTREE:" -ForegroundColor Green
Write-Host "  frontend/index.html" 
Write-Host "  frontend/src/components/public/PublicLandingHero.tsx" 
Write-Host "  frontend/src/pages/Landing.tsx" 
Write-Host "  frontend/src/services/auth.service.ts" 
Write-Host "  frontend/src/types/auth.ts" 
Write-Host "  frontend/src/pages/Login.tsx" 
Write-Host "  frontend/src/pages/Register.tsx" 
Write-Host "" 
Write-Host "NO git commands executed." -ForegroundColor Yellow
Write-Host "NO build/test commands executed." -ForegroundColor Yellow
