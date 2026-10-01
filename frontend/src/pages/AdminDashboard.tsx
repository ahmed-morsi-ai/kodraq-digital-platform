import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import { Ban, Check, Loader2, RefreshCw, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { adminEnrollmentService } from "@/services/adminEnrollment.service";
import type { AdminEnrollment } from "@/types/enrollment";

function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return "Unable to load enrollment records right now.";
}

function statusLabel(status: string): string {
  if (status === "active") return "Active";
  if (status === "pending") return "Pending review";
  if (status === "cancelled") return "Revoked";
  if (status === "pending_payment") return "Pending payment";
  if (status === "completed") return "Completed";
  return status;
}

function statusClass(status: string): string {
  if (status === "active") return "bg-emerald-50 text-emerald-800";
  if (status === "cancelled") return "bg-red-50 text-red-800";
  if (status === "completed") return "bg-blue-50 text-blue-800";
  return "bg-amber-50 text-amber-800";
}

export default function AdminDashboard() {
  const [enrollments, setEnrollments] = useState<AdminEnrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadEnrollments = useCallback(
    () => adminEnrollmentService.getAll(),
    [],
  );

  const applyEnrollments = useCallback((data: AdminEnrollment[]) => {
    setEnrollments(data);
    setError(null);
  }, []);

  const applyLoadError = useCallback((requestError: unknown) => {
    setError(getErrorMessage(requestError));
  }, []);

  useEffect(() => {
    let active = true;
    void loadEnrollments()
      .then((data) => {
        if (active) applyEnrollments(data);
      })
      .catch((requestError: unknown) => {
        if (active) applyLoadError(requestError);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applyEnrollments, applyLoadError, loadEnrollments]);

  const refresh = () => {
    setIsLoading(true);
    setNotice(null);
    void loadEnrollments()
      .then(applyEnrollments)
      .catch(applyLoadError)
      .finally(() => setIsLoading(false));
  };

  const updateStatus = async (enrollment: AdminEnrollment) => {
    const nextStatus = enrollment.status === "active" ? "cancelled" : "active";
    setBusyId(enrollment.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await adminEnrollmentService.updateStatus(
        enrollment.id,
        nextStatus,
      );
      setEnrollments((current) =>
        current.map((item) => item.id === updated.id ? updated : item),
      );
      setNotice(
        `${updated.student_name}'s access ${nextStatus === "active" ? "activated" : "revoked"}.`,
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="w-full px-5 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase text-sky-700">
              <ShieldCheck aria-hidden="true" className="size-4" /> Administration
            </p>
            <h1 className="mt-2 text-3xl font-black text-slate-950">
              Student enrollments
            </h1>
          </div>
          <Button type="button" variant="outline" onClick={refresh} disabled={isLoading}>
            <RefreshCw aria-hidden="true" className={isLoading ? "size-4 animate-spin" : "size-4"} />
            Refresh
          </Button>
        </header>

        {notice && (
          <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-800">
            {error}
          </p>
        )}

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-0">
            {isLoading ? (
              <div role="status" className="flex items-center justify-center gap-2 p-12 text-sm text-slate-600">
                <Loader2 aria-hidden="true" className="size-4 animate-spin" />
                Loading enrollments...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                    <tr>
                      <th className="px-5 py-3">Student</th>
                      <th className="px-5 py-3">Track</th>
                      <th className="px-5 py-3">Enrolled</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Access</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {enrollments.map((enrollment) => {
                      const isActive = enrollment.status === "active";
                      return (
                        <tr key={enrollment.id}>
                          <td className="px-5 py-4">
                            <p className="font-semibold text-slate-900">{enrollment.student_name}</p>
                            <p className="mt-1 text-xs text-slate-500">{enrollment.student_email}</p>
                          </td>
                          <td className="px-5 py-4 font-medium text-slate-700">{enrollment.track_name}</td>
                          <td className="px-5 py-4 text-slate-600">
                            {new Date(enrollment.enrolled_at).toLocaleDateString()}
                          </td>
                          <td className="px-5 py-4">
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(enrollment.status)}`}>
                              {statusLabel(enrollment.status)}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-right">
                            <Button
                              type="button"
                              size="sm"
                              variant={isActive ? "outline" : "default"}
                              disabled={busyId === enrollment.id}
                              onClick={() => void updateStatus(enrollment)}
                            >
                              {busyId === enrollment.id ? (
                                <Loader2 aria-hidden="true" className="size-4 animate-spin" />
                              ) : isActive ? (
                                <Ban aria-hidden="true" className="size-4" />
                              ) : (
                                <Check aria-hidden="true" className="size-4" />
                              )}
                              {isActive ? "Revoke" : "Activate"}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                    {enrollments.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                          No enrollments found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}