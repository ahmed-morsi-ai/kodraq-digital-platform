import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, BookOpen, Loader2, RefreshCw } from "lucide-react";
import { isAxiosError } from "axios";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import TrackCard from "@/components/TrackCard";
import { enrollmentService } from "@/services/enrollment.service";
import { trackService } from "@/services/track.service";
import type { Enrollment } from "@/types/enrollment";
import type { TrackSummary } from "@/types/track";

function getApiErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      return "The server rejected the request. Please check your access and try again.";
    }

    if (error.response?.status === 403) {
      return "You do not have permission to access your learning data.";
    }

    if (error.response?.status === 500) {
      return "The server encountered an unexpected error.";
    }
  }

  return "Unable to load tracks right now. Please try again.";
}

export default function Tracks() {
  const navigate = useNavigate();

  const [tracks, setTracks] = useState<TrackSummary[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTracks = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [trackData, enrollmentData] = await Promise.all([
        trackService.getActiveTracks(),
        enrollmentService.getMyEnrollments(),
      ]);

      setTracks(trackData);
      setEnrollments(enrollmentData);
    } catch (requestError) {
      console.error("Failed to load tracks", requestError);
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTracks();
  }, [loadTracks]);

  const enrollmentByTrack = useMemo(() => {
    return new Map(enrollments.map((enrollment) => [enrollment.track_id, enrollment]));
  }, [enrollments]);

  const handleOpenTrack = (trackId: number) => {
    navigate(`/tracks/${trackId}`);
  };

  return (
    <div className="w-full px-6 py-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div className="max-w-2xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                <BookOpen className="h-3.5 w-3.5" />
                Learning tracks
              </div>

              <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                Explore technical tracks
              </h2>

              <p className="mt-3 text-sm leading-6 text-gray-500 md:text-base">
                Discover the active Kodraq Digital tracks and choose the
                learning path that matches your goals.
              </p>
            </div>

            {!isLoading && !error && tracks.length > 0 && (
              <div className="text-sm text-gray-500">
                {tracks.length} active {tracks.length === 1 ? "track" : "tracks"}
              </div>
            )}
          </div>
        </section>

        {isLoading && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Card key={index} className="border-gray-200 shadow-sm">
                <CardContent className="space-y-5 p-6">
                  <div className="flex items-center justify-between">
                    <div className="h-11 w-11 animate-pulse rounded-xl bg-gray-200" />
                    <div className="h-6 w-28 animate-pulse rounded-full bg-gray-200" />
                  </div>

                  <div className="space-y-3">
                    <div className="h-6 w-3/4 animate-pulse rounded bg-gray-200" />
                    <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
                    <div className="h-4 w-5/6 animate-pulse rounded bg-gray-100" />
                  </div>

                  <div className="h-10 w-full animate-pulse rounded-lg bg-gray-200" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!isLoading && error && (
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col items-center justify-center px-6 py-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
                <AlertCircle className="h-6 w-6" />
              </div>

              <h3 className="mt-4 text-lg font-semibold text-red-900">
                Unable to load tracks
              </h3>

              <p className="mt-2 max-w-lg text-sm leading-6 text-red-700">
                {error}
              </p>

              <Button
                type="button"
                variant="outline"
                className="mt-6 gap-2 border-red-200 bg-white text-red-700 hover:bg-red-100"
                onClick={() => void loadTracks()}
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && tracks.length === 0 && (
          <Card className="border-gray-200 shadow-sm">
            <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                <BookOpen className="h-7 w-7" />
              </div>

              <h3 className="mt-5 text-xl font-semibold text-slate-900">
                No active tracks yet
              </h3>

              <p className="mt-2 max-w-lg text-sm leading-6 text-gray-500">
                There are currently no active learning tracks available.
                Please check again later.
              </p>
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && tracks.length > 0 && (
          <section>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {tracks.map((track) => (
                <TrackCard
                  key={track.id}
                  track={track}
                  enrollment={enrollmentByTrack.get(track.id)}
                  onOpenTrack={handleOpenTrack}
                />
              ))}
            </div>
          </section>
        )}

        {isLoading && (
          <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading your learning tracks...
          </div>
        )}
      </div>
    </div>
  );
}
