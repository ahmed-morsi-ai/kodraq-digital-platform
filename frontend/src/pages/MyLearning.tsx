import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { enrollmentService } from "@/services/enrollment.service";
import { trackService } from "@/services/track.service";
import type { Enrollment } from "@/types/enrollment";
import type { TrackSummary } from "@/types/track";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return "Unable to load your learning area right now.";
}

function getStatusMeta(status: Enrollment["status"]) {
  switch (status) {
    case "active":
      return {
        label: "Active",
        className: "bg-emerald-50 text-emerald-700",
        icon: CheckCircle2,
      };
    case "completed":
      return {
        label: "Completed",
        className: "bg-blue-50 text-blue-700",
        icon: CheckCircle2,
      };
    case "cancelled":
      return {
        label: "Cancelled",
        className: "bg-red-50 text-red-700",
        icon: XCircle,
      };
    default:
      return {
        label: status,
        className: "bg-slate-100 text-slate-600",
        icon: Clock3,
      };
  }
}

export default function MyLearning() {
  const navigate = useNavigate();

  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [tracks, setTracks] = useState<TrackSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLearning = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [enrollmentData, trackData] = await Promise.all([
        enrollmentService.getMyEnrollments(),
        trackService.getActiveTracks(),
      ]);

      setEnrollments(enrollmentData);
      setTracks(trackData);
    } catch (requestError) {
      console.error("Failed to load learning area", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLearning();
  }, [loadLearning]);

  const trackById = new Map(
    tracks.map((track) => [track.id, track]),
  );

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-81px)] items-center justify-center px-6">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600" />
          <p className="mt-4 text-sm text-gray-500">
            Loading your learning area...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full px-6 py-10">
        <Card className="mx-auto max-w-3xl border-red-200 bg-red-50">
          <CardContent className="flex flex-col items-center py-14 text-center">
            <h2 className="text-xl font-semibold text-red-900">
              Unable to load My Learning
            </h2>
            <p className="mt-2 text-sm text-red-700">{error}</p>

            <Button
              type="button"
              variant="outline"
              className="mt-6 gap-2"
              onClick={() => void loadLearning()}
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const activeEnrollments = enrollments.filter(
    (enrollment) => enrollment.status !== "cancelled",
  );

  return (
    <div className="w-full px-6 py-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section>
          <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            <BookOpen className="h-3.5 w-3.5" />
            My Learning
          </div>

          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            Your learning tracks
          </h1>

          <p className="mt-2 text-sm leading-6 text-gray-500">
            Continue your enrolled tracks and access their curriculum.
          </p>
        </section>

        {activeEnrollments.length === 0 ? (
          <Card className="border-gray-200 shadow-sm">
            <CardContent className="flex flex-col items-center py-16 text-center">
              <BookOpen className="h-10 w-10 text-gray-400" />

              <h2 className="mt-5 text-xl font-semibold text-slate-900">
                No active enrollments
              </h2>

              <p className="mt-2 max-w-lg text-sm text-gray-500">
                You have not enrolled in a learning track yet.
              </p>

              <Button
                type="button"
                className="mt-6 gap-2 bg-blue-600 text-white hover:bg-blue-700"
                onClick={() => navigate("/tracks")}
              >
                Browse tracks
                <ArrowRight className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {activeEnrollments.map((enrollment) => {
              const track = trackById.get(enrollment.track_id);
              const statusMeta = getStatusMeta(enrollment.status);
              const StatusIcon = statusMeta.icon;

              return (
                <Card
                  key={enrollment.id}
                  className="border-gray-200 shadow-sm"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                        <BookOpen className="h-5 w-5" />
                      </div>

                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusMeta.className}`}
                      >
                        <StatusIcon className="h-3.5 w-3.5" />
                        {statusMeta.label}
                      </span>
                    </div>

                    <CardTitle className="pt-2">
                      {track?.name || `Track #${enrollment.track_id}`}
                    </CardTitle>

                    <CardDescription>
                      {track?.description ||
                        "Continue your enrolled learning track."}
                    </CardDescription>
                  </CardHeader>

                  <CardContent>
                    <Button
                      type="button"
                      className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
                      onClick={() =>
                        navigate(`/tracks/${enrollment.track_id}`)
                      }
                    >
                      Open track
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
