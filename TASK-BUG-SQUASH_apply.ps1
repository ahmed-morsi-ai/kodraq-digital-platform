$ErrorActionPreference = "Stop"

$repo = (Get-Location).Path

function Assert-Path([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "Required path not found: $Path"
    }
}

function Read-Utf8Strict([string]$Path) {
    $encoding = [System.Text.UTF8Encoding]::new($false, $true)
    return [System.IO.File]::ReadAllText((Resolve-Path $Path), $encoding)
}

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText(
        (Resolve-Path $Path),
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Write-NewUtf8NoBom([string]$RelativePath, [string]$Content) {
    $full = Join-Path $repo $RelativePath
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

Write-Host "TASK-BUG-SQUASH audit/apply starting..." -ForegroundColor Cyan

$required = @(
    ".\frontend\index.html",
    ".\frontend\src\App.tsx",
    ".\frontend\src\pages\Landing.tsx",
    ".\frontend\src\pages\Login.tsx",
    ".\frontend\src\pages\Register.tsx",
    ".\frontend\src\components\public\PublicLandingHero.tsx",
    ".\frontend\src\services\auth.service.ts",
    ".\frontend\src\types\auth.ts"
)
foreach ($path in $required) { Assert-Path $path }

# 1) Enforce explicit UTF-8 HTML metadata.
Write-NewUtf8NoBom ".\frontend\index.html" @'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Kodraq Digital — Learn. Build. Automate." />
    <title>Kodraq Digital</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'@

# 2) Normalize every frontend .tsx file to strict UTF-8 (no BOM) without changing its content.
$tsxFiles = Get-ChildItem ".\frontend\src" -Recurse -File -Filter *.tsx
foreach ($file in $tsxFiles) {
    $content = Read-Utf8Strict $file.FullName
    [System.IO.File]::WriteAllText(
        $file.FullName,
        $content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

# 3) Rewrite the public hero in clean UTF-8 and make the single persona selection functional.
Write-NewUtf8NoBom ".\frontend\src\components\public\PublicLandingHero.tsx" @'
import { GraduationCap, Briefcase, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export default function PublicLandingHero() {
  return (
    <section
      id="paths"
      className="relative min-h-screen bg-white px-6 pb-16 pt-24 text-slate-900 md:px-12"
      dir="rtl"
    >
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
        <div className="absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-[#E0F0FF] opacity-60 blur-3xl" />
      </div>

      <div className="container relative z-10 mx-auto flex min-h-[calc(100vh-6rem)] max-w-7xl flex-col justify-center">
        <div className="mx-auto mb-16 max-w-3xl text-center">
          <div className="mb-5 text-xs font-bold uppercase tracking-[0.3em] text-[#5B9BD5]">
            Kodraq Digital
          </div>

          <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 md:text-6xl">
            مستقبلك الرقمي يبدأ مع{" "}
            <span className="text-[#5B9BD5]">Kodraq</span>
          </h1>

          <p className="text-lg font-medium leading-relaxed text-slate-500 md:text-xl">
            سواء كنت تطمح لبناء مسيرتك في التقنية أو تبحث عن حلول برمجية
            ترتقي بأعمالك، Kodraq تساعدك على الانتقال من الفكرة إلى نتيجة
            حقيقية.
          </p>
        </div>

        <div className="mx-auto grid w-full max-w-5xl gap-8 md:grid-cols-2">
          <Link
            to="/register?persona=trainee"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 transition-all duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <GraduationCap size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا <span dir="ltr" className="inline-block text-[#5B9BD5]">Trainee</span>
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Academy
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                ابدأ رحلتك مع برامج تدريبية مكثفة في Technical Tracks حقيقية،
                وتعلّم من خلال Practical Tasks وProjects تساعدك على بناء مهاراتك
                والاستعداد لسوق العمل.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>ابدأ رحلتك التعليمية</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </Link>

          <a
            href="#services"
            className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white p-10 transition-all duration-300 hover:-translate-y-1 hover:border-sky-200 hover:shadow-2xl hover:shadow-[#E0F0FF]"
          >
            <div>
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0F7FF] text-[#5B9BD5] shadow-sm transition-colors group-hover:bg-[#5B9BD5] group-hover:text-white">
                <Briefcase size={32} strokeWidth={1.5} />
              </div>

              <h2 className="mb-2 text-3xl font-bold text-slate-900">
                أنا <span dir="ltr" className="inline-block text-[#5B9BD5]">Client</span>
              </h2>

              <h3 className="mb-6 text-lg font-bold uppercase tracking-widest text-[#5B9BD5]">
                Kodraq Services
              </h3>

              <p className="mb-8 leading-relaxed text-slate-600">
                حوّل فكرتك إلى Digital Product قابل للتوسع من خلال Web &amp;
                Software Development وAI Automation وUI/UX وCloud Solutions
                مصممة باحتياجات عملك.
              </p>
            </div>

            <div className="mt-auto flex items-center font-bold text-slate-800 transition-colors group-hover:text-[#5B9BD5]">
              <span>اكتشف Kodraq Services</span>
              <ArrowLeft className="mr-3 h-5 w-5 transition-transform group-hover:-translate-x-2" />
            </div>
          </a>
        </div>
      </div>
    </section>
  );
}
'@

# 4) Remove the duplicated persona section from Landing.tsx. The hero is now the single source of truth.
Write-NewUtf8NoBom ".\frontend\src\pages\Landing.tsx" @'
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

        <section id="how-it-works" className="border-b border-slate-200 bg-white py-20">
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
                  <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
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

# 5) Align AuthService exactly with backend routes/schemas.
Write-NewUtf8NoBom ".\frontend\src\services\auth.service.ts" @'
import { api } from "./api";
import type {
  LoginCredentials,
  RegisterCredentials,
  TokenResponse,
  User,
} from "@/types/auth";

export const AuthService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new URLSearchParams();
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
  },

  async register(credentials: RegisterCredentials): Promise<User> {
    const payload = {
      email: credentials.email.trim(),
      full_name: credentials.full_name.trim(),
      password: credentials.password,
    };

    const response = await api.post<User>("/api/v1/users", payload);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/users/me");
    return response.data;
  },
};
'@

# 6) Ensure the auth types contain exactly the backend registration contract.
Write-NewUtf8NoBom ".\frontend\src\types\auth.ts" @'
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

export interface RegisterCredentials {
  email: string;
  full_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
'@

# 7) Guarantee detailed auth diagnostics in both auth page catch blocks.
$loginPath = ".\frontend\src\pages\Login.tsx"
$login = Read-Utf8Strict $loginPath
if ($login -notmatch 'console\.error\("Login failed", requestError\)') {
    $login = $login.Replace(
'    } catch (requestError) {',
'    } catch (requestError) {`r`n      console.error("Login failed", requestError);'
    )
    Write-Utf8NoBom $loginPath $login
}

$registerPath = ".\frontend\src\pages\Register.tsx"
$register = Read-Utf8Strict $registerPath
if ($register -notmatch 'console\.error\("Registration failed", requestError\)') {
    $register = $register.Replace(
'    } catch (requestError) {',
'    } catch (requestError) {`r`n      console.error("Registration failed", requestError);'
    )
    Write-Utf8NoBom $registerPath $register
}

# 8) Re-normalize changed TSX files to UTF-8 after all edits.
foreach ($path in @(
    ".\frontend\src\pages\Landing.tsx",
    ".\frontend\src\pages\Login.tsx",
    ".\frontend\src\pages\Register.tsx",
    ".\frontend\src\components\public\PublicLandingHero.tsx"
)) {
    $content = Read-Utf8Strict $path
    Write-Utf8NoBom $path $content
}

Write-Host "" 
Write-Host "TASK-BUG-SQUASH apply complete." -ForegroundColor Green
Write-Host "No git commands were executed." -ForegroundColor Yellow
