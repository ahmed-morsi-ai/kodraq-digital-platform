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
