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
    enrollment?.status === "active" ||
    enrollment?.status === "completed";

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
