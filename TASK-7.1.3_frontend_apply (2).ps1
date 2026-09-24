$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Location).Path
$FrontendRoot = Join-Path $RepoRoot "frontend"

if (-not (Test-Path $FrontendRoot)) {
    throw "Run this script from the Kodraq Digital repository root. Expected: $FrontendRoot"
}

function Read-Utf8 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
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
    Write-Utf8NoBom $Path ($text.Replace($Old, $New))
}

function Replace-TextLiteral {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Description
    )
    if (-not $Text.Contains($Old)) {
        throw "Text patch anchor not found for $Description"
    }
    return $Text.Replace($Old, $New)
}

function Ensure-Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Description
    )
    $text = Read-Utf8 $Path
    if (-not $text.Contains($Needle)) {
        throw "Audit check failed for $Description in $Path"
    }
}

$requiredFiles = @(
    "src\App.tsx",
    "src\layouts\RootLayout.tsx",
    "src\pages\TrackDetail.tsx",
    "src\types\auth.ts",
    "src\types\enrollment.ts",
    "src\types\track.ts",
    "src\services\api.ts",
    "src\services\enrollment.service.ts",
    "src\components\EnrollmentPanel.tsx",
    "src\components\ProtectedRoute.tsx",
    "src\components\ui\button.tsx",
    "src\components\ui\card.tsx",
    "src\components\ui\input.tsx",
    "src\components\ui\label.tsx"
)

Write-Host "===== TASK-7.1.3 FRONTEND AUDIT =====" -ForegroundColor Cyan
foreach ($relative in $requiredFiles) {
    $path = Join-Path $FrontendRoot $relative
    if (-not (Test-Path $path)) {
        throw "Required audited frontend file is missing: $path"
    }
    Write-Host "AUDIT PASS: $relative"
}

$apiPath = Join-Path $FrontendRoot "src\services\api.ts"
$apiText = Read-Utf8 $apiPath
if ($apiText -notmatch 'axios\.create') {
    throw "Expected Axios API client was not found in src/services/api.ts"
}

$trackPath = Join-Path $FrontendRoot "src\types\track.ts"
$trackText = Read-Utf8 $trackPath
if ($trackText -notmatch 'is_premium\s*:') {
    $trackText = Replace-TextLiteral `
        -Text $trackText `
        -Old "  ordering: number;`r`n  modules?: TrackModule[];" `
        -New "  ordering: number;`r`n  price: number;`r`n  currency: string;`r`n  is_premium: boolean;`r`n  modules?: TrackModule[];" `
        -Description "TrackCurriculum pricing fields"

    $trackText = Replace-TextLiteral `
        -Text $trackText `
        -Old "  ordering: number;`r`n}" `
        -New "  ordering: number;`r`n  price: number;`r`n  currency: string;`r`n  is_premium: boolean;`r`n}" `
        -Description "TrackSummary pricing fields"

    Write-Utf8NoBom $trackPath $trackText
}

$enrollmentText = Read-Utf8 $enrollmentTypePath
if ($enrollmentText -notmatch 'cancelled') {
    throw "Expected enrollment status union was not found."
}

$authTypePath = Join-Path $FrontendRoot "src\types\auth.ts"
$authText = Read-Utf8 $authTypePath
if ($authText -notmatch 'is_superuser') {
    throw "Expected auth user type with is_superuser was not found."
}

$trackDetailPath = Join-Path $FrontendRoot "src\pages\TrackDetail.tsx"
$trackDetailText = Read-Utf8 $trackDetailPath
if ($trackDetailText -notmatch 'EnrollmentPanel') {
    throw "Expected existing enrollment UI was not found in TrackDetail.tsx"
}

$rootLayoutPath = Join-Path $FrontendRoot "src\layouts\RootLayout.tsx"
$rootLayoutText = Read-Utf8 $rootLayoutPath
if ($rootLayoutText -notmatch '\{ label: "My Learning", href: "/my-learning" \},') {
    throw "RootLayout navigation anchor is not in the audited expected form. Aborting before write."
}

Write-Host "AUDIT PASS: existing enrollment flow, auth, routing, API client, and main navigation are present." -ForegroundColor Green

# ------------------------------------------------------------
# 1. Frontend payment types
# ------------------------------------------------------------
$paymentTypes = @'
export type PaymentStatus =
  | "PENDING_VERIFICATION"
  | "VERIFIED"
  | "REJECTED";

export type PaymentMethod = "VODAFONE_CASH" | "INSTAPAY";

export interface PaymentInstructions {
  vodafone_cash: string;
  instapay: string;
}

export interface Payment {
  id: number;
  user_id: number;
  track_id: number;
  amount: number | string;
  currency: string;
  status: PaymentStatus;
  payment_method: string;
  receipt_url: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentVerificationPayload {
  status: "VERIFIED" | "REJECTED";
  rejection_reason?: string | null;
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\types\payment.ts") $paymentTypes

# ------------------------------------------------------------
# 2. Payment service — FormData is explicit for receipt upload
# ------------------------------------------------------------
$paymentService = @'
import { api } from "./api";
import type {
  Payment,
  PaymentInstructions,
  PaymentVerificationPayload,
} from "@/types/payment";

export const paymentService = {
  async getInstructions(): Promise<PaymentInstructions> {
    const response = await api.get<PaymentInstructions>("/payments/instructions");
    return response.data;
  },

  async submitPayment(
    trackId: number,
    method: string,
    receiptFile: File,
  ): Promise<Payment> {
    const formData = new FormData();
    formData.append("track_id", String(trackId));
    formData.append("payment_method", method);
    formData.append("receipt", receiptFile);

    const response = await api.post<Payment>("/payments/submit", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  },

  async getMyPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/payments/me");
    return response.data;
  },

  async getAdminPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/payments", {
      params: { status: "PENDING_VERIFICATION" },
    });
    return response.data;
  },

  async verifyPayment(
    paymentId: number,
    status: "VERIFIED" | "REJECTED",
    rejectionReason?: string,
  ): Promise<Payment> {
    const payload: PaymentVerificationPayload = {
      status,
      rejection_reason:
        status === "REJECTED" ? rejectionReason?.trim() || null : null,
    };

    const response = await api.patch<Payment>(
      `/payments/${paymentId}/verify`,
      payload,
    );
    return response.data;
  },
};
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\services\payment.service.ts") $paymentService

# ------------------------------------------------------------
# 3. Update frontend domain types for monetized tracks / pending state
# ------------------------------------------------------------
$trackText = Read-Utf8 $trackPath
if ($trackText -notmatch 'is_premium\s*:') {
    $trackText = Replace-TextLiteral `
        -Text $trackText `
        -Old "  ordering: number;`r`n  modules?: TrackModule[];" `
        -New "  ordering: number;`r`n  price: number;`r`n  currency: string;`r`n  is_premium: boolean;`r`n  modules?: TrackModule[];" `
        -Description "TrackCurriculum pricing fields"
    $trackText = Replace-TextLiteral `
        -Text $trackText `
        -Old "  ordering: number;`r`n}" `
        -New "  ordering: number;`r`n  price: number;`r`n  currency: string;`r`n  is_premium: boolean;`r`n}" `
        -Description "TrackSummary pricing fields"
    Write-Utf8NoBom $trackPath $trackText
}

$enrollmentText = Read-Utf8 $enrollmentTypePath
$enrollmentText = Replace-TextLiteral `
    -Text $enrollmentText `
    -Old '"active" | "completed" | "cancelled"' `
    -New '"active" | "completed" | "cancelled" | "pending_payment"' `
    -Description "Enrollment pending_payment state"
Write-Utf8NoBom $enrollmentTypePath $enrollmentText

$authText = Read-Utf8 $authTypePath
if ($authText -notmatch 'role\??\s*:\s*string') {
    if ($authText -notmatch 'is_superuser\??\s*:\s*boolean;') {
        throw "Could not safely locate User.is_superuser in src/types/auth.ts"
    }
    $authText = Replace-TextLiteral `
        -Text $authText `
        -Old "  is_superuser: boolean;" `
        -New "  is_superuser: boolean;`r`n  role?: string | null;" `
        -Description "User role field"
    Write-Utf8NoBom $authTypePath $authText
}

# ------------------------------------------------------------
# 4. Student premium checkout / receipt upload component
# ------------------------------------------------------------
$checkout = @'
import { FormEvent, useEffect, useMemo, useState } from "react";
import { isAxiosError } from "axios";
import {
  CheckCircle2,
  CreditCard,
  FileImage,
  Loader2,
  ShieldCheck,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { enrollmentService } from "@/services/enrollment.service";
import { paymentService } from "@/services/payment.service";
import type { Enrollment } from "@/types/enrollment";
import type { PaymentInstructions } from "@/types/payment";
import type { TrackCurriculum } from "@/types/track";

interface PaymentCheckoutProps {
  track: TrackCurriculum;
  enrollment?: Enrollment;
  onEnrollmentCreated: (enrollment: Enrollment) => void;
}

function getApiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  return "We could not complete the payment step. Please try again.";
}

function formatAmount(amount: number, currency: string): string {
  return `${new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)} ${currency}`;
}

export default function PaymentCheckout({
  track,
  enrollment,
  onEnrollmentCreated,
}: PaymentCheckoutProps) {
  const [instructions, setInstructions] = useState<PaymentInstructions | null>(null);
  const [method, setMethod] = useState("VODAFONE_CASH");
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(
    enrollment?.status === "pending_payment",
  );
  const [isEnrollmentSubmitting, setIsEnrollmentSubmitting] = useState(false);
  const [isPaymentSubmitting, setIsPaymentSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const hasPendingPayment = enrollment?.status === "pending_payment";
  const isAlreadyEnrolled =
    enrollment !== undefined &&
    enrollment.status !== "cancelled" &&
    enrollment.status !== "pending_payment";

  useEffect(() => {
    if (!isCheckoutOpen) {
      return;
    }

    let active = true;
    setError(null);

    void paymentService
      .getInstructions()
      .then((data) => {
        if (active) {
          setInstructions(data);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(getApiErrorMessage(requestError));
        }
      });

    return () => {
      active = false;
    };
  }, [isCheckoutOpen]);

  const amount = useMemo(
    () => Number(track.price ?? 0),
    [track.price],
  );

  if (!track.is_premium || isAlreadyEnrolled) {
    return null;
  }

  async function handleStartCheckout() {
    setError(null);
    setSuccess(false);
    setIsEnrollmentSubmitting(true);

    try {
      const created = await enrollmentService.enroll({
        track_id: track.id,
        status: "active",
      });
      onEnrollmentCreated(created);
      setIsCheckoutOpen(true);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsEnrollmentSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(false);

    if (!receiptFile) {
      setError("Choose the payment receipt screenshot before submitting.");
      return;
    }

    setIsPaymentSubmitting(true);

    try {
      await paymentService.submitPayment(track.id, method, receiptFile);
      setReceiptFile(null);
      setSuccess(true);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsPaymentSubmitting(false);
    }
  }

  if (hasPendingPayment || isCheckoutOpen) {
    return (
      <Card className="border-amber-200 bg-amber-50/50 shadow-sm">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-slate-900">
                {hasPendingPayment
                  ? "Pending Admin Verification"
                  : "Complete your payment"}
              </CardTitle>
              <CardDescription className="mt-1">
                {hasPendingPayment
                  ? "Your enrollment is waiting for payment verification. Submit the receipt below if you have not already done so."
                  : "Send the track fee using one of the available methods, then upload the receipt screenshot."}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 bg-white p-4 md:col-span-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Amount due
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {formatAmount(amount, track.currency)}
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 md:col-span-2">
              <p className="text-sm font-semibold text-slate-900">Payment instructions</p>
              {instructions ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium text-gray-500">Vodafone Cash</p>
                    <p className="mt-1 font-mono text-sm font-semibold text-slate-900">
                      {instructions.vodafone_cash}
                    </p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium text-gray-500">InstaPay</p>
                    <p className="mt-1 break-all font-mono text-sm font-semibold text-slate-900">
                      {instructions.instapay}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading payment instructions...
                </div>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-gray-200 bg-white p-5">
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="payment-method">Payment method</Label>
                <select
                  id="payment-method"
                  value={method}
                  onChange={(event) => setMethod(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="VODAFONE_CASH">Vodafone Cash</option>
                  <option value="INSTAPAY">InstaPay</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="receipt-file">Receipt screenshot</Label>
                <Input
                  id="receipt-file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) =>
                    setReceiptFile(event.target.files?.[0] ?? null)
                  }
                  className="cursor-pointer"
                />
              </div>
            </div>

            {receiptFile && (
              <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
                <FileImage className="h-4 w-4 shrink-0" />
                <span className="truncate">{receiptFile.name}</span>
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            {success && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                Receipt submitted. Your payment is now pending admin verification.
              </div>
            )}

            <Button
              type="submit"
              disabled={isPaymentSubmitting || !receiptFile}
              className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
            >
              {isPaymentSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading receipt...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Submit receipt
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 shadow-sm">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <CreditCard className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-slate-900">Premium enrollment</CardTitle>
            <CardDescription className="mt-1">
              Enroll in {track.name} for {formatAmount(amount, track.currency)}. You will then upload your payment receipt for admin verification.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <Button
          type="button"
          disabled={isEnrollmentSubmitting}
          onClick={() => void handleStartCheckout()}
          className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
        >
          {isEnrollmentSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Starting checkout...
            </>
          ) : (
            <>
              <CreditCard className="h-4 w-4" />
              Enroll & pay
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\components\PaymentCheckout.tsx") $checkout

# ------------------------------------------------------------
# 5. Admin verification dashboard
# ------------------------------------------------------------
$adminPayments = @'
import { useCallback, useEffect, useMemo, useState } from "react";
import { isAxiosError } from "axios";
import { CheckCircle2, ExternalLink, Loader2, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { Navigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { paymentService } from "@/services/payment.service";
import type { Payment } from "@/types/payment";
import { useAuth } from "@/context/AuthContext";

function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  return "Unable to load or update payments right now.";
}

function getReceiptUrl(receiptPath: string): string {
  if (/^https?:\/\//i.test(receiptPath)) {
    return receiptPath;
  }

  const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
  const origin = new URL(apiUrl, window.location.origin).origin;
  return `${origin}/${receiptPath.replace(/^\/+/, "")}`;
}

function formatAmount(amount: number | string, currency: string): string {
  return `${new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount))} ${currency}`;
}

export default function AdminPayments() {
  const { user } = useAuth();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [busyPaymentId, setBusyPaymentId] = useState<number | null>(null);
  const [rejectionReasons, setRejectionReasons] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const canAccess = Boolean(user?.is_superuser || user?.role === "admin");

  const loadPayments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await paymentService.getAdminPayments();
      setPayments(data.filter((payment) => payment.status === "PENDING_VERIFICATION"));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canAccess) {
      void loadPayments();
    }
  }, [canAccess, loadPayments]);

  const pendingCount = useMemo(() => payments.length, [payments]);

  if (!canAccess) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleVerify(paymentId: number, status: "VERIFIED" | "REJECTED") {
    setBusyPaymentId(paymentId);
    setError(null);

    try {
      await paymentService.verifyPayment(
        paymentId,
        status,
        status === "REJECTED" ? rejectionReasons[paymentId] : undefined,
      );
      setRejectionReasons((current) => {
        const next = { ...current };
        delete next[paymentId];
        return next;
      });
      setPayments((current) => current.filter((payment) => payment.id !== paymentId));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyPaymentId(null);
    }
  }

  return (
    <div className="w-full px-6 py-8 md:py-12">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
              Payment Verification
            </h1>
            <p className="mt-2 text-sm text-gray-500 md:text-base">
              Review receipt uploads and verify premium enrollments.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => void loadPayments()}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <Card className="border-gray-200 shadow-sm">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>Pending payments</CardTitle>
                <CardDescription>{pendingCount} payment{pendingCount === 1 ? "" : "s"} awaiting verification.</CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {error && (
              <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-12 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading pending payments...
              </div>
            ) : payments.length === 0 ? (
              <div className="py-12 text-center">
                <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-600" />
                <p className="mt-3 text-lg font-semibold text-slate-900">No pending payments</p>
                <p className="mt-1 text-sm text-gray-500">Everything currently submitted has been reviewed.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {payments.map((payment) => {
                  const receiptUrl = getReceiptUrl(payment.receipt_url);
                  const isBusy = busyPaymentId === payment.id;
                  const rejectionReason = rejectionReasons[payment.id] ?? "";

                  return (
                    <div
                      key={payment.id}
                      className="grid gap-5 rounded-xl border border-gray-200 bg-white p-5 lg:grid-cols-[minmax(0,1fr)_220px]"
                    >
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Payment</p>
                          <p className="mt-1 font-semibold text-slate-900">#{payment.id}</p>
                          <p className="mt-1 text-xs text-gray-500">Track #{payment.track_id}</p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Amount</p>
                          <p className="mt-1 text-lg font-bold text-slate-900">
                            {formatAmount(payment.amount, payment.currency)}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Method</p>
                          <p className="mt-1 font-medium text-slate-900">{payment.payment_method}</p>
                          <p className="mt-1 text-xs text-gray-500">User #{payment.user_id}</p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Receipt</p>
                          <a
                            href={receiptUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-800"
                          >
                            <ExternalLink className="h-4 w-4" />
                            Open receipt
                          </a>
                        </div>

                        <div className="sm:col-span-2 lg:col-span-4">
                          <label className="text-xs font-semibold uppercase tracking-wide text-gray-400" htmlFor={`reject-reason-${payment.id}`}>
                            Rejection reason (required when rejecting)
                          </label>
                          <textarea
                            id={`reject-reason-${payment.id}`}
                            value={rejectionReason}
                            onChange={(event) =>
                              setRejectionReasons((current) => ({
                                ...current,
                                [payment.id]: event.target.value,
                              }))
                            }
                            rows={2}
                            placeholder="Optional for approval; recommended for rejection."
                            className="mt-2 w-full rounded-md border border-gray-200 px-3 py-2 text-sm shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>

                      <div className="flex flex-col justify-end gap-2">
                        <a
                          href={receiptUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="flex min-h-28 items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-gray-50"
                        >
                          <img
                            src={receiptUrl}
                            alt={`Payment receipt #${payment.id}`}
                            className="max-h-40 w-full object-contain"
                            loading="lazy"
                          />
                        </a>

                        <Button
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleVerify(payment.id, "VERIFIED")}
                          className="gap-2 bg-emerald-600 text-white hover:bg-emerald-700"
                        >
                          {isBusy && busyPaymentId === payment.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <CheckCircle2 className="h-4 w-4" />
                          )}
                          Approve
                        </Button>

                        <Button
                          type="button"
                          variant="outline"
                          disabled={isBusy || rejectionReason.trim().length === 0}
                          onClick={() => void handleVerify(payment.id, "REJECTED")}
                          className="gap-2 border-red-200 text-red-700 hover:bg-red-50"
                        >
                          <XCircle className="h-4 w-4" />
                          Reject
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
'@
Write-Utf8NoBom (Join-Path $FrontendRoot "src\pages\AdminPayments.tsx") $adminPayments

# ------------------------------------------------------------
# 6. Integrate premium checkout into TrackDetail without replacing free enrollment
# ------------------------------------------------------------
$trackDetailText = Read-Utf8 $trackDetailPath
if ($trackDetailText -notmatch 'PaymentCheckout') {
    $trackDetailText = Replace-TextLiteral `
        -Text $trackDetailText `
        -Old 'import EnrollmentPanel from "@/components/EnrollmentPanel";' `
        -New 'import EnrollmentPanel from "@/components/EnrollmentPanel";`r`nimport PaymentCheckout from "@/components/PaymentCheckout";' `
        -Description "TrackDetail payment checkout import"
}

$enrollmentPanelBlock = @'
            <EnrollmentPanel
              trackId={numericTrackId}
              enrollment={currentEnrollment}
              onEnrollmentCreated={handleEnrollmentCreated}
            />
'@
$paymentAwareBlock = @'
            {track?.is_premium ? (
              <PaymentCheckout
                track={track}
                enrollment={currentEnrollment}
                onEnrollmentCreated={handleEnrollmentCreated}
              />
            ) : (
              <EnrollmentPanel
                trackId={numericTrackId}
                enrollment={currentEnrollment}
                onEnrollmentCreated={handleEnrollmentCreated}
              />
            )}
'@
if ($trackDetailText.Contains($enrollmentPanelBlock)) {
    $trackDetailText = $trackDetailText.Replace($enrollmentPanelBlock, $paymentAwareBlock)
} elseif ($trackDetailText -notmatch 'PaymentCheckout') {
    throw "Could not locate the existing EnrollmentPanel block in TrackDetail.tsx"
}
Write-Utf8NoBom $trackDetailPath $trackDetailText

# ------------------------------------------------------------
# 7. Route AdminPayments
# ------------------------------------------------------------
$appPath = Join-Path $FrontendRoot "src\App.tsx"
$appText = Read-Utf8 $appPath
if ($appText -notmatch 'AdminPayments') {
    $appText = Replace-TextLiteral `
        -Text $appText `
        -Old 'import Tracks from "./pages/Tracks";' `
        -New 'import Tracks from "./pages/Tracks";`r`nimport AdminPayments from "./pages/AdminPayments";' `
        -Description "AdminPayments import"
    $routeAnchor = '            <Route path="/my-learning" element={<MyLearning />} />'
    $routeReplacement = @'
            <Route path="/my-learning" element={<MyLearning />} />
            <Route path="/admin/payments" element={<AdminPayments />} />
'@
    if (-not $appText.Contains($routeAnchor)) {
        throw "App.tsx MyLearning route anchor not found."
    }
    $appText = $appText.Replace($routeAnchor, $routeReplacement.TrimEnd())
}
Write-Utf8NoBom $appPath $appText

# ------------------------------------------------------------
# 8. Main navigation — only admin/superuser sees Payments
# ------------------------------------------------------------
$rootLayoutText = Read-Utf8 $rootLayoutPath
if ($rootLayoutText -notmatch 'AdminPayments') {
    if ($rootLayoutText -notmatch 'useAuth') {
        if ($rootLayoutText -match 'import { Outlet, NavLink } from "react-router-dom";') {
            $rootLayoutText = Replace-TextLiteral `
                -Text $rootLayoutText `
                -Old 'import { Outlet, NavLink } from "react-router-dom";' `
                -New 'import { Outlet, NavLink } from "react-router-dom";`r`nimport { useAuth } from "@/context/AuthContext";' `
                -Description "RootLayout useAuth import"
        } elseif ($rootLayoutText -match 'import { Outlet } from "react-router-dom";') {
            $rootLayoutText = Replace-TextLiteral `
                -Text $rootLayoutText `
                -Old 'import { Outlet } from "react-router-dom";' `
                -New 'import { Outlet } from "react-router-dom";`r`nimport { useAuth } from "@/context/AuthContext";' `
                -Description "RootLayout useAuth import"
        }
        if ($rootLayoutText -notmatch 'useAuth') {
            throw "Could not safely add useAuth to RootLayout.tsx."
        }
        $functionMatch = [regex]::Match($rootLayoutText, 'function\s+RootLayout\s*\(\)\s*\{')
        if (-not $functionMatch.Success) {
            throw "Could not locate RootLayout function for role-aware navigation patch."
        }
        $insertAt = $functionMatch.Index + $functionMatch.Length
        $rootLayoutText = $rootLayoutText.Insert($insertAt, "`r`n  const { user } = useAuth();")
    } elseif ($rootLayoutText -notmatch 'const\s*\{[^}]*user[^}]*\}\s*=\s*useAuth\(\)') {
        $functionMatch = [regex]::Match($rootLayoutText, 'function\s+RootLayout\s*\(\)\s*\{')
        if (-not $functionMatch.Success) {
            throw "Could not locate RootLayout function for user access patch."
        }
        $insertAt = $functionMatch.Index + $functionMatch.Length
        $rootLayoutText = $rootLayoutText.Insert($insertAt, "`r`n  const { user } = useAuth();")
    }

    $navAnchor = '{ label: "My Learning", href: "/my-learning" },'
    $navReplacement = @'
  { label: "My Learning", href: "/my-learning" },
  ...(user?.is_superuser || user?.role === "admin"
    ? [{ label: "Payments", href: "/admin/payments" }]
    : []),
'@
    if (-not $rootLayoutText.Contains($navAnchor)) {
        throw "RootLayout My Learning navigation anchor was not found after audit."
    }
    $rootLayoutText = $rootLayoutText.Replace($navAnchor, $navReplacement.TrimEnd())
}
Write-Utf8NoBom $rootLayoutPath $rootLayoutText

Write-Host "" 
Write-Host "===== TASK-7.1.3 FILES WRITTEN =====" -ForegroundColor Green
Write-Host "Created: src/types/payment.ts"
Write-Host "Created: src/services/payment.service.ts"
Write-Host "Created: src/components/PaymentCheckout.tsx"
Write-Host "Created: src/pages/AdminPayments.tsx"
Write-Host "Patched: src/types/track.ts"
Write-Host "Patched: src/types/enrollment.ts"
Write-Host "Patched: src/types/auth.ts"
Write-Host "Patched: src/pages/TrackDetail.tsx"
Write-Host "Patched: src/App.tsx"
Write-Host "Patched: src/layouts/RootLayout.tsx"
Write-Host "No git commit was created."

# ------------------------------------------------------------
# 9. Frontend verification gates
# ------------------------------------------------------------
Push-Location $FrontendRoot
try {
    Write-Host ""
    Write-Host "===== TYPESCRIPT CHECK =====" -ForegroundColor Cyan
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw "TypeScript check failed." }

    Write-Host ""
    Write-Host "===== OXLINT =====" -ForegroundColor Cyan
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw "oxlint failed." }

    Write-Host ""
    Write-Host "===== PRODUCTION BUILD =====" -ForegroundColor Cyan
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Production build failed." }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "TASK-7.1.3 FRONTEND VERIFICATION PASSED." -ForegroundColor Green
Write-Host "No git commit was created."
