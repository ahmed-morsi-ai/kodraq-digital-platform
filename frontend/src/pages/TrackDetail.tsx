import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  FileText,
  Layers3,
  Loader2,
  PlayCircle,
  RefreshCw,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { trackService } from "@/services/track.service";
import type { TrackCurriculum } from "@/types/track";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (error.response?.status === 404) {
      return "This track could not be found or is no longer active.";
    }

    if (error.response?.status === 403) {
      return "You do not have permission to access this curriculum.";
    }

    if (error.response?.status === 500) {
      return "The server encountered an unexpected error.";
    }
  }

  return "Unable to load this curriculum right now. Please try again.";
}

export default function TrackDetail() {
  const { trackId } = useParams<{ trackId: string }>();
  const navigate = useNavigate();

  const [track, setTrack] = useState<TrackCurriculum | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const numericTrackId = Number(trackId);
  const isValidTrackId =
    Number.isInteger(numericTrackId) && numericTrackId > 0;

  const loadCurriculum = useCallback(async () => {
    if (!isValidTrackId) {
      setError("The requested track ID is invalid.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const curriculum =
        await trackService.getCurriculum(numericTrackId);

      setTrack(curriculum);
    } catch (requestError) {
      console.error("Failed to load track curriculum", requestError);
      setTrack(null);
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, [isValidTrackId, numericTrackId]);

  useEffect(() => {
    void loadCurriculum();
  }, [loadCurriculum]);

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-81px)] w-full items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>

          <h2 className="mt-5 text-lg font-semibold text-slate-900">
            Loading curriculum
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Preparing modules, lessons, and resources...
          </p>
        </div>
      </div>
    );
  }

  if (error || !track) {
    return (
      <div className="w-full px-6 py-10">
        <div className="mx-auto max-w-3xl">
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-14 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600">
                <BookOpen className="h-7 w-7" />
              </div>

              <h2 className="mt-5 text-xl font-semibold text-red-900">
                Unable to load curriculum
              </h2>

              <p className="mt-2 max-w-lg text-sm leading-6 text-red-700">
                {error || "The requested track is unavailable."}
              </p>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  className="gap-2 border-red-200 bg-white"
                  onClick={() => navigate("/tracks")}
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to tracks
                </Button>

                <Button
                  type="button"
                  className="gap-2 bg-blue-600 text-white hover:bg-blue-700"
                  onClick={() => void loadCurriculum()}
                >
                  <RefreshCw className="h-4 w-4" />
                  Try again
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-6 py-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <Button
          type="button"
          variant="ghost"
          className="gap-2 px-0 text-gray-500 hover:bg-transparent hover:text-slate-900"
          onClick={() => navigate("/tracks")}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to tracks
        </Button>

        <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 bg-gradient-to-br from-blue-50 via-white to-white p-6 md:p-8">
            <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
              <div className="max-w-3xl">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                  <BookOpen className="h-3.5 w-3.5" />
                  Learning track
                </div>

                <h1 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
                  {track.name}
                </h1>

                <p className="mt-4 text-sm leading-7 text-gray-600 md:text-base">
                  {track.description ||
                    "Explore the complete curriculum for this learning track."}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 md:min-w-[220px]">
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <Layers3 className="h-5 w-5 text-blue-600" />
                  <p className="mt-3 text-2xl font-bold text-slate-900">
                    {track.modules.length}
                  </p>
                  <p className="text-xs text-gray-500">
                    {track.modules.length === 1 ? "Module" : "Modules"}
                  </p>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <FileText className="h-5 w-5 text-emerald-600" />
                  <p className="mt-3 text-2xl font-bold text-slate-900">
                    {track.modules.reduce(
                      (total, module) => total + module.resources.length,
                      0,
                    )}
                  </p>
                  <p className="text-xs text-gray-500">
                    Resources
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-5">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Curriculum
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Follow the modules, lessons, and supporting resources in order.
            </p>
          </div>

          {track.modules.length === 0 ? (
            <Card className="border-gray-200 shadow-sm">
              <CardContent className="flex flex-col items-center px-6 py-14 text-center">
                <Layers3 className="h-8 w-8 text-gray-400" />
                <h3 className="mt-4 text-lg font-semibold text-slate-900">
                  No modules available yet
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  This track does not have curriculum modules published yet.
                </p>
              </CardContent>
            </Card>
          ) : (
            track.modules.map((module, moduleIndex) => (
              <Card
                key={module.id}
                className="overflow-hidden border-gray-200 shadow-sm"
              >
                <CardHeader className="border-b border-gray-100 bg-gray-50/70">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white">
                      {String(moduleIndex + 1).padStart(2, "0")}
                    </div>

                    <div className="min-w-0">
                      <CardTitle className="text-xl text-slate-900">
                        {module.title}
                      </CardTitle>

                      <CardDescription className="mt-2 max-w-3xl leading-6">
                        {module.description || "Module description unavailable."}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-6 p-5 md:p-6">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                      <BookOpen className="h-4 w-4 text-blue-600" />
                      Lessons
                      <span className="text-xs font-normal text-gray-400">
                        ({module.lessons.length})
                      </span>
                    </div>

                    {module.lessons.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
                        No lessons have been published for this module yet.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {module.lessons.map((lesson, lessonIndex) => (
                          <div
                            key={lesson.id}
                            className="rounded-xl border border-gray-200 bg-white p-4 transition-colors hover:border-blue-200 hover:bg-blue-50/30"
                          >
                            <div className="flex gap-3">
                              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-semibold text-slate-600">
                                {lessonIndex + 1}
                              </div>

                              <div className="min-w-0 flex-1">
                                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                  <div>
                                    <h4 className="font-semibold text-slate-900">
                                      {lesson.title}
                                    </h4>

                                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-600">
                                      {lesson.content || "No lesson content available."}
                                    </p>
                                  </div>

                                  {lesson.video_url && (
                                    <a
                                      href={lesson.video_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700"
                                    >
                                      <PlayCircle className="h-4 w-4" />
                                      Video
                                      <ExternalLink className="h-3.5 w-3.5" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                      <FileText className="h-4 w-4 text-emerald-600" />
                      Resources
                      <span className="text-xs font-normal text-gray-400">
                        ({module.resources.length})
                      </span>
                    </div>

                    {module.resources.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
                        No resources have been published for this module yet.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        {module.resources.map((resource) => (
                          <a
                            key={resource.id}
                            href={resource.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="group rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-emerald-200 hover:bg-emerald-50/30"
                          >
                            <div className="flex items-start gap-3">
                              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                                <FileText className="h-4 w-4" />
                              </div>

                              <div className="min-w-0 flex-1">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <p className="font-medium text-slate-900 group-hover:text-emerald-700">
                                      {resource.title}
                                    </p>

                                    <p className="mt-1 text-xs uppercase tracking-wide text-gray-400">
                                      {resource.resource_type}
                                    </p>
                                  </div>

                                  <ExternalLink className="h-4 w-4 shrink-0 text-gray-400 group-hover:text-emerald-600" />
                                </div>
                              </div>
                            </div>
                          </a>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    This module is available in the published curriculum.
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </section>
      </div>
    </div>
  );
}
