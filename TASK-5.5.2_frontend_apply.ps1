$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $RepoRoot "frontend"

if (-not (Test-Path $FrontendRoot)) {
    throw "Could not find frontend directory: $FrontendRoot"
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $Path,
        $Content.TrimEnd() + "`r`n",
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Read-Utf8 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.Encoding]::UTF8
    )
}

function Replace-Exact {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $text = Read-Utf8 $Path
    if (-not $text.Contains($Old)) {
        throw "Patch anchor not found for $Description in $Path"
    }

    $patched = $text.Replace($Old, $New)
    Write-Utf8NoBom $Path $patched
}

# ------------------------------------------------------------
# AUDIT GATE
# ------------------------------------------------------------
$requiredFiles = @(
    "src\App.tsx",
    "src\pages\MyLearning.tsx",
    "src\layouts\RootLayout.tsx",
    "src\services\api.ts",
    "src\services\finalProject.service.ts",
    "src\types\finalProject.ts",
    "src\components\ui\button.tsx",
    "src\components\ui\card.tsx"
)

foreach ($relative in $requiredFiles) {
    $path = Join-Path $FrontendRoot $relative
    if (-not (Test-Path $path)) {
        throw "Required audited frontend file is missing: $path"
    }
}

# ------------------------------------------------------------
# 1. frontend/src/types/certificate.ts
# ------------------------------------------------------------
$certificateTypes = @'
export type CertificateStatus = "ISSUED" | "REVOKED";

export interface Certificate {
  id: number;
  student_id: number;
  track_id: number;
  graduation_result_id: number;
  certificate_number: string;
  final_score: number | null;
  status: CertificateStatus | string;
  file_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificateVerification {
  valid: boolean;
  certificate_number: string;
  student_name: string;
  track_name: string;
  issue_date: string;
  status?: string;
  final_score?: number | null;
}

export interface GraduationGateCheck {
  id: number;
  evaluation_id: number;
  gate_key: string;
  passed: boolean;
  actual_value: number | null;
  required_value: number | null;
  failure_reason: string | null;
  details: Record<string, unknown> | null;
}

export interface GraduationEvaluation {
  id: number;
  user_id: number;
  track_id: number;
  overall_score: number | null;
  is_eligible: boolean;
  status: string;
  evaluated_at: string | null;
  created_at: string;
  updated_at: string;
  gate_checks: GraduationGateCheck[];
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\types\certificate.ts") $certificateTypes

# ------------------------------------------------------------
# 2. frontend/src/services/certificate.service.ts
#
# Frontend contract:
#   POST /api/v1/graduation/graduate
#       body: { track_id }
#       response: issued Certificate
#
#   GET /api/v1/certificates/me
#   GET /api/v1/certificates/verify/{code}
#
# The existing axios baseURL remains untouched.
# ------------------------------------------------------------
$certificateService = @'
import { api } from "./api";
import type {
  Certificate,
  CertificateVerification,
} from "@/types/certificate";

export const certificateService = {
  async graduate(trackId: number): Promise<Certificate> {
    const response = await api.post<Certificate>("/graduation/graduate", {
      track_id: trackId,
    });

    return response.data;
  },

  async getMyCertificates(): Promise<Certificate[]> {
    const response = await api.get<Certificate[]>("/certificates/me");
    return response.data;
  },

  async verifyCertificate(code: string): Promise<CertificateVerification> {
    const response = await api.get<CertificateVerification>(
      `/certificates/verify/${encodeURIComponent(code)}`,
    );

    return response.data;
  },
};
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\services\certificate.service.ts") $certificateService

# ------------------------------------------------------------
# 3. frontend/src/components/GraduationClaimCard.tsx
#    Student trigger lives inside MyLearning, which satisfies the
#    Track Dashboard / MyLearning requirement without duplicating
#    TrackDetail's large curriculum component.
# ------------------------------------------------------------
$graduationClaim = @'
import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  Award,
  CheckCircle2,
  ExternalLink,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { certificateService } from "@/services/certificate.service";
import { finalProjectService } from "@/services/finalProject.service";
import type { Certificate } from "@/types/certificate";
import type { ProjectSubmission } from "@/types/finalProject";

interface GraduationClaimCardProps {
  trackId: number;
  trackName: string;
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return "Unable to complete graduation right now. Please try again.";
}

export default function GraduationClaimCard({
  trackId,
  trackName,
}: GraduationClaimCardProps) {
  const [submission, setSubmission] = useState<ProjectSubmission | null>(null);
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isClaiming, setIsClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const loadGraduationState = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [project, submissions, certificates] = await Promise.all([
        finalProjectService.getByTrack(trackId),
        finalProjectService.getMySubmissions(),
        certificateService.getMyCertificates(),
      ]);

      const latestSubmission =
        submissions
          .filter((item) => item.project_id === project.id)
          .sort(
            (a, b) =>
              new Date(b.updated_at).getTime() -
              new Date(a.updated_at).getTime(),
          )[0] ?? null;

      const existingCertificate =
        certificates.find((item) => item.track_id === trackId) ?? null;

      setSubmission(latestSubmission);
      setCertificate(existingCertificate);
    } catch (requestError) {
      console.error("Failed to load graduation state", requestError);
      setSubmission(null);
      setCertificate(null);
      setError(null);
    } finally {
      setIsLoading(false);
    }
  }, [trackId]);

  useEffect(() => {
    void loadGraduationState();
  }, [loadGraduationState]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setToast(null);
    }, 5000);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [toast]);

  const handleGraduate = async () => {
    setIsClaiming(true);
    setError(null);

    try {
      const issuedCertificate = await certificateService.graduate(trackId);
      setCertificate(issuedCertificate);
      setToast("Congratulations — your Kodraq Digital certificate is ready.");
    } catch (requestError) {
      console.error("Graduation request failed", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setIsClaiming(false);
    }
  };

  if (isLoading || !submission || submission.status !== "APPROVED") {
    return null;
  }

  return (
    <>
      <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-white shadow-sm">
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Final project approved
              </div>

              <CardTitle className="mt-3 flex items-center gap-2 text-xl text-slate-900">
                <Award className="h-5 w-5 text-emerald-600" />
                Graduation & certificate
              </CardTitle>

              <CardDescription className="mt-2">
                Your final project for {trackName} has been approved.
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {certificate ? (
            <div className="rounded-2xl border border-emerald-200 bg-white p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Certificate issued
                  </p>

                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {certificate.certificate_number}
                  </p>

                  <p className="mt-1 text-sm text-gray-500">
                    Issued{" "}
                    {new Date(certificate.created_at).toLocaleDateString()}
                    {certificate.final_score !== null
                      ? ` · Final score ${certificate.final_score}/100`
                      : ""}
                  </p>
                </div>

                <Button
                  asChild
                  variant="outline"
                  className="gap-2 border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                >
                  <Link
                    to={`/verify/${encodeURIComponent(
                      certificate.certificate_number,
                    )}`}
                  >
                    Verify certificate
                    <ExternalLink className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-emerald-200 bg-white p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                      <ShieldCheck className="h-5 w-5" />
                    </div>

                    <div>
                      <p className="font-semibold text-slate-900">
                        You are ready to graduate
                      </p>
                      <p className="mt-1 text-sm leading-6 text-gray-500">
                        Claim your official Kodraq Digital certificate for this
                        track.
                      </p>
                    </div>
                  </div>

                  <Button
                    type="button"
                    disabled={isClaiming}
                    onClick={() => void handleGraduate()}
                    className="gap-2 bg-emerald-600 text-white hover:bg-emerald-700"
                  >
                    {isClaiming ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Award className="h-4 w-4" />
                    )}
                    {isClaiming ? "Graduating..." : "Claim Certificate"}
                  </Button>
                </div>
              </div>

              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border border-emerald-200 bg-slate-950 px-4 py-3 text-sm font-medium text-white shadow-xl"
        >
          {toast}
        </div>
      )}
    </>
  );
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\components\GraduationClaimCard.tsx") $graduationClaim

# ------------------------------------------------------------
# 4. frontend/src/pages/MyCertificates.tsx
# ------------------------------------------------------------
$myCertificates = @'
import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  Award,
  ExternalLink,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { certificateService } from "@/services/certificate.service";
import type { Certificate } from "@/types/certificate";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return "Unable to load your certificates right now.";
}

export default function MyCertificates() {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCertificates = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await certificateService.getMyCertificates();
      setCertificates(data);
    } catch (requestError) {
      console.error("Failed to load certificates", requestError);
      setCertificates([]);
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCertificates();
  }, [loadCertificates]);

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>

          <h1 className="mt-5 text-lg font-semibold text-slate-900">
            Loading certificates
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            Retrieving your earned credentials...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-6 py-8 md:py-12">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-950 via-slate-950 to-slate-900 p-6 text-white shadow-xl md:p-10">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-200">
                <Award className="h-3.5 w-3.5" />
                Kodraq credentials
              </div>

              <h1 className="mt-5 text-3xl font-black tracking-tight md:text-5xl">
                My Certificates
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/60 md:text-base">
                Keep your verified graduation credentials in one place and
                share them with employers or clients.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-center">
              <p className="text-3xl font-black text-emerald-300">
                {certificates.length}
              </p>
              <p className="text-xs uppercase tracking-[0.18em] text-white/40">
                Certificates
              </p>
            </div>
          </div>
        </section>

        {error && (
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm leading-6 text-red-700">{error}</p>
              <Button
                type="button"
                variant="outline"
                onClick={() => void loadCertificates()}
                className="gap-2 border-red-200 bg-white"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        {certificates.length === 0 ? (
          <Card className="border-gray-200 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <ShieldCheck className="h-8 w-8" />
              </div>

              <h2 className="mt-5 text-xl font-semibold text-slate-900">
                No certificates yet
              </h2>

              <p className="mt-2 max-w-lg text-sm leading-6 text-gray-500">
                Complete and pass your final project, then return here to
                manage your issued certificates.
              </p>

              <Button
                asChild
                className="mt-6 bg-blue-600 text-white hover:bg-blue-700"
              >
                <Link to="/my-learning">Back to My Learning</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {certificates.map((certificate) => (
              <Card
                key={certificate.id}
                className="overflow-hidden border-gray-200 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                <CardHeader className="border-b border-gray-100 bg-gradient-to-br from-emerald-50 via-white to-white">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                      <Award className="h-5 w-5" />
                    </div>

                    <span className="inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                      {certificate.status}
                    </span>
                  </div>

                  <div>
                    <CardTitle className="mt-4 text-lg text-slate-900">
                      Graduation Certificate
                    </CardTitle>
                    <CardDescription className="mt-2 break-all text-xs">
                      {certificate.certificate_number}
                    </CardDescription>
                  </div>
                </CardHeader>

                <CardContent className="space-y-5 p-6">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                        Issued
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {new Date(
                          certificate.created_at,
                        ).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                        Final score
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {certificate.final_score !== null
                          ? `${certificate.final_score}/100`
                          : "—"}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      asChild
                      className="flex-1 gap-2 bg-slate-950 text-white hover:bg-slate-800"
                    >
                      <Link
                        to={`/verify/${encodeURIComponent(
                          certificate.certificate_number,
                        )}`}
                      >
                        <ShieldCheck className="h-4 w-4" />
                        Verify
                      </Link>
                    </Button>

                    {certificate.file_url && (
                      <Button
                        asChild
                        variant="outline"
                        className="gap-2"
                      >
                        <a
                          href={certificate.file_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open file
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\pages\MyCertificates.tsx") $myCertificates

# ------------------------------------------------------------
# 5. frontend/src/pages/VerifyCertificate.tsx
#    Public /verify/:code route.
# ------------------------------------------------------------
$verifyCertificate = @'
import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  Award,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Search,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { certificateService } from "@/services/certificate.service";
import type { CertificateVerification } from "@/types/certificate";

function getInvalidState(error: unknown) {
  if (isAxiosError(error) && error.response?.status === 404) {
    return "Certificate Not Found / Invalid";
  }

  return "Certificate Not Found / Invalid";
}

export default function VerifyCertificate() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<CertificateVerification | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [invalid, setInvalid] = useState(false);

  const verify = useCallback(async () => {
    if (!code?.trim()) {
      setInvalid(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setInvalid(false);

    try {
      const verification = await certificateService.verifyCertificate(code);
      setResult(verification);
    } catch (error) {
      console.error("Certificate verification failed", error);
      setResult(null);
      setInvalid(true);
    } finally {
      setIsLoading(false);
    }
  }, [code]);

  useEffect(() => {
    void verify();
  }, [verify]);

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-10 text-white md:py-16">
      <div className="mx-auto flex min-h-[calc(100vh-80px)] max-w-5xl items-center justify-center">
        {isLoading ? (
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-300">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>

            <h1 className="mt-6 text-2xl font-bold">
              Verifying certificate
            </h1>

            <p className="mt-2 text-sm text-white/50">
              Checking the credential against Kodraq Digital records...
            </p>
          </div>
        ) : invalid || !result?.valid ? (
          <Card className="w-full max-w-2xl border-red-300/20 bg-white text-slate-900 shadow-2xl">
            <CardContent className="flex flex-col items-center px-6 py-14 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 text-red-600">
                <XCircle className="h-8 w-8" />
              </div>

              <h1 className="mt-6 text-2xl font-bold">
                Certificate Not Found / Invalid
              </h1>

              <p className="mt-3 max-w-lg text-sm leading-6 text-gray-500">
                The certificate code could not be verified against Kodraq
                Digital&apos;s public credential records.
              </p>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  onClick={() => void verify()}
                  className="gap-2 bg-slate-950 text-white hover:bg-slate-800"
                >
                  <Search className="h-4 w-4" />
                  Try again
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/")}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back home
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="w-full max-w-4xl">
            <div className="mb-8 text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-xs font-semibold text-emerald-200">
                <ShieldCheck className="h-4 w-4" />
                Verified credential
              </div>

              <h1 className="mt-5 text-3xl font-black tracking-tight md:text-5xl">
                Certificate Verification
              </h1>

              <p className="mt-3 text-sm text-white/50">
                This credential has been verified by Kodraq Digital.
              </p>
            </div>

            <Card className="overflow-hidden border-emerald-200 bg-white text-slate-900 shadow-2xl">
              <div className="border-b border-emerald-100 bg-gradient-to-br from-emerald-950 via-slate-950 to-slate-900 p-6 text-white md:p-10">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-300/10 text-emerald-300">
                      <Award className="h-7 w-7" />
                    </div>

                    <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200/60">
                      Kodraq Digital
                    </p>

                    <h2 className="mt-2 text-3xl font-black">
                      Graduation Certificate
                    </h2>
                  </div>

                  <div className="inline-flex items-center gap-2 self-start rounded-full bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
                    <CheckCircle2 className="h-4 w-4" />
                    Verified by Kodraq Digital
                  </div>
                </div>
              </div>

              <CardContent className="space-y-6 p-6 md:p-10">
                <div className="grid gap-5 md:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Student
                    </p>
                    <p className="mt-2 text-xl font-bold text-slate-900">
                      {result.student_name}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Track
                    </p>
                    <p className="mt-2 text-xl font-bold text-slate-900">
                      {result.track_name}
                    </p>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Issue date
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-800">
                      {new Date(result.issue_date).toLocaleDateString()}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Certificate number
                    </p>
                    <p className="mt-2 break-all text-sm font-semibold text-slate-800">
                      {result.certificate_number}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
                    <div>
                      <p className="font-semibold text-emerald-900">
                        Verified by Kodraq Digital
                      </p>
                      <p className="mt-1 text-sm leading-6 text-emerald-800/80">
                        This public verification result confirms that the
                        certificate number belongs to a credential recorded by
                        Kodraq Digital.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-between">
                  <Button
                    asChild
                    variant="outline"
                    className="gap-2"
                  >
                    <Link to="/">
                      <ArrowLeft className="h-4 w-4" />
                      Kodraq Digital
                    </Link>
                  </Button>

                  <Button
                    type="button"
                    onClick={() => window.print()}
                    className="bg-slate-950 text-white hover:bg-slate-800"
                  >
                    Print verification
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\pages\VerifyCertificate.tsx") $verifyCertificate

# ------------------------------------------------------------
# 6. Patch MyLearning.tsx
# ------------------------------------------------------------
$myLearningPath = Join-Path $FrontendRoot "src\pages\MyLearning.tsx"
$myLearning = Read-Utf8 $myLearningPath

$myLearningImportAnchor = 'import { enrollmentService } from "@/services/enrollment.service";'
$myLearningImportReplacement = @'
import GraduationClaimCard from "@/components/GraduationClaimCard";
import { enrollmentService } from "@/services/enrollment.service";
'@.TrimEnd()

if ($myLearning -notmatch 'from "@/components/GraduationClaimCard";') {
    if (-not $myLearning.Contains($myLearningImportAnchor)) {
        throw "MyLearning import anchor not found."
    }
    $myLearning = $myLearning.Replace(
        $myLearningImportAnchor,
        $myLearningImportReplacement
    )
}

$myLearningCardAnchor = @'
                </CardContent>

                <CardFooter className="flex flex-col gap-2 pt-0 sm:flex-row">
'@
$myLearningCardReplacement = @'
                </CardContent>

                <div className="px-6 pb-5">
                  <GraduationClaimCard
                    trackId={data.track.id}
                    trackName={data.track.name}
                  />
                </div>

                <CardFooter className="flex flex-col gap-2 pt-0 sm:flex-row">
'@

if ($myLearning -notmatch '<GraduationClaimCard') {
    if (-not $myLearning.Contains($myLearningCardAnchor)) {
        throw "MyLearning card insertion anchor not found."
    }
    $myLearning = $myLearning.Replace(
        $myLearningCardAnchor,
        $myLearningCardReplacement
    )
}

Write-Utf8NoBom $myLearningPath $myLearning

# ------------------------------------------------------------
# 7. Patch App.tsx
# ------------------------------------------------------------
$appPath = Join-Path $FrontendRoot "src\App.tsx"
$app = Read-Utf8 $appPath

if ($app -notmatch 'from "./pages/MyCertificates";') {
    $app = $app.Replace(
        'import MyLearning from "./pages/MyLearning";',
        'import MyLearning from "./pages/MyLearning";' + "`r`n" +
        'import MyCertificates from "./pages/MyCertificates";'
    )
}

if ($app -notmatch 'from "./pages/VerifyCertificate";') {
    $app = $app.Replace(
        'import Tracks from "./pages/Tracks";',
        'import Tracks from "./pages/Tracks";' + "`r`n" +
        'import VerifyCertificate from "./pages/VerifyCertificate";'
    )
}

if ($app -notmatch 'path="/verify/:code"') {
    $loginRoute = @'
        <Route path="/login" element={<Login />} />
'@
    $replacement = @'
        <Route path="/login" element={<Login />} />
        <Route path="/verify/:code" element={<VerifyCertificate />} />
'@
    if (-not $app.Contains($loginRoute)) {
        throw "App.tsx login route anchor not found."
    }
    $app = $app.Replace($loginRoute, $replacement)
}

if ($app -notmatch 'path="/certificates"') {
    $learningRoute = @'
            <Route path="/my-learning" element={<MyLearning />} />
'@
    $replacement = @'
            <Route path="/my-learning" element={<MyLearning />} />
            <Route path="/certificates" element={<MyCertificates />} />
'@
    if (-not $app.Contains($learningRoute)) {
        throw "App.tsx MyLearning route anchor not found."
    }
    $app = $app.Replace($learningRoute, $replacement)
}

Write-Utf8NoBom $appPath $app

# ------------------------------------------------------------
# 8. Patch RootLayout.tsx
# ------------------------------------------------------------
$layoutPath = Join-Path $FrontendRoot "src\layouts\RootLayout.tsx"
$layout = Read-Utf8 $layoutPath

if ($layout -notmatch 'href: "/certificates"') {
    $navAnchor = '{ label: "My Learning", href: "/my-learning" },'
    $navReplacement = @'
  { label: "My Learning", href: "/my-learning" },
  { label: "Certificates", href: "/certificates" },
'@
    if (-not $layout.Contains($navAnchor)) {
        throw "RootLayout navigation anchor not found."
    }
    $layout = $layout.Replace($navAnchor, $navReplacement.TrimEnd())
}

Write-Utf8NoBom $layoutPath $layout

# ------------------------------------------------------------
# 9. Format + verify
# ------------------------------------------------------------
Push-Location $FrontendRoot
try {
    Write-Host ""
    Write-Host "TASK-5.5.2 frontend files written. No git commit was created." -ForegroundColor Green
    Write-Host ""
    Write-Host "Running TypeScript..."
    npx tsc --noEmit

    if ($LASTEXITCODE -ne 0) {
        throw "TypeScript check failed."
    }

    Write-Host ""
    Write-Host "Running oxlint..."
    npx oxlint

    if ($LASTEXITCODE -ne 0) {
        throw "oxlint failed."
    }

    Write-Host ""
    Write-Host "Running production build..."
    npm run build

    if ($LASTEXITCODE -ne 0) {
        throw "Production build failed."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "TASK-5.5.2 FRONTEND VERIFY COMMANDS COMPLETED." -ForegroundColor Green
Write-Host "No git commit was created."
Write-Host ""
Write-Host "Backend API contract required by the frontend:"
Write-Host "  POST /api/v1/graduation/graduate  { track_id } -> issued Certificate"
Write-Host "  GET  /api/v1/certificates/me"
Write-Host "  GET  /api/v1/certificates/verify/{code}"
