import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { isAxiosError } from "axios";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { enrollmentService } from "@/services/enrollment.service";
import type { Enrollment } from "@/types/enrollment";

interface EnrollmentPanelProps {
  trackId: number;
  enrollment?: Enrollment;
  onEnrollmentCreated: (enrollment: Enrollment) => void;
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    if (status === 409) {
      return "You are already enrolled in this track.";
    }

    if (status === 400 && typeof detail === "string") {
      return detail;
    }

    if (status === 403) {
      return "Your account is not allowed to enroll in this track.";
    }
  }

  return "Unable to complete enrollment right now. Please try again.";
}

export default function EnrollmentPanel({
  trackId,
  enrollment,
  onEnrollmentCreated,
}: EnrollmentPanelProps) {
  const navigate = useNavigate();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const isActive = enrollment?.status === "active";
  const isCompleted = enrollment?.status === "completed";
  const isCancelled = enrollment?.status === "cancelled";

  const handleEnroll = async () => {
    setIsSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      const createdEnrollment = await enrollmentService.enroll({
        track_id: trackId,
      });

      onEnrollmentCreated(createdEnrollment);
      setSuccess(true);
    } catch (requestError) {
      console.error("Enrollment failed", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="border-gray-200 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ShieldCheck className="h-5 w-5 text-blue-600" />
          Enrollment
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {isActive && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
              <div>
                <p className="font-semibold text-emerald-900">
                  You are enrolled
                </p>
                <p className="mt-1 text-sm leading-6 text-emerald-700">
                  Your enrollment is active. Continue to your learning area
                  to track your progress.
                </p>
              </div>
            </div>

            <Button
              type="button"
              className="mt-4 w-full bg-emerald-600 text-white hover:bg-emerald-700"
              onClick={() => navigate("/my-learning")}
            >
              Go to My Learning
            </Button>
          </div>
        )}

        {isCompleted && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
              <div>
                <p className="font-semibold text-blue-900">
                  Track completed
                </p>
                <p className="mt-1 text-sm leading-6 text-blue-700">
                  You have completed this track.
                </p>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              className="mt-4 w-full border-blue-200 bg-white"
              onClick={() => navigate("/my-learning")}
            >
              View My Learning
            </Button>
          </div>
        )}

        {isCancelled && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="font-semibold text-amber-900">
              Previous enrollment was cancelled
            </p>
            <p className="mt-1 text-sm leading-6 text-amber-700">
              You can submit a new enrollment request.
            </p>

            <Button
              type="button"
              className="mt-4 w-full bg-blue-600 text-white hover:bg-blue-700"
              disabled={isSubmitting}
              onClick={() => void handleEnroll()}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enrolling...
                </>
              ) : (
                "Enroll again"
              )}
            </Button>
          </div>
        )}

        {!enrollment && (
          <div>
            <p className="text-sm leading-6 text-gray-500">
              Join this learning track to start building your curriculum
              progress and access your learning dashboard.
            </p>

            <Button
              type="button"
              className="mt-4 w-full bg-blue-600 text-white hover:bg-blue-700"
              disabled={isSubmitting}
              onClick={() => void handleEnroll()}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating enrollment...
                </>
              ) : (
                "Enroll in this track"
              )}
            </Button>
          </div>
        )}

        {success && (
          <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            Enrollment created successfully.
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
