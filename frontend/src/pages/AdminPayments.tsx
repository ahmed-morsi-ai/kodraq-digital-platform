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
