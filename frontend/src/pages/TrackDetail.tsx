import { useCallback, useEffect, useMemo, useState } from "react";
import { isAxiosError } from "axios";
import {
  ArrowLeft,
  BookOpen,
  Check,
  CheckCircle2,
  Circle,
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
import AssignmentList from "@/components/AssignmentList";
import EnrollmentPanel from "@/components/EnrollmentPanel";
import { assignmentService } from "@/services/assignment.service";
import { enrollmentService } from "@/services/enrollment.service";
import { trackService } from "@/services/track.service";
import type { Assignment } from "@/types/assignment";
import type { Enrollment } from "@/types/enrollment";
import type {
  LessonProgress,
  ProgressStatus,
} from "@/types/progress";
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

function getProgressLabel(status?: ProgressStatus) {
  switch (status) {
    case "in_progress":
      return "In progress";
    case "completed":
      return "Completed";
    default:
      return "Not started";
  }
}

export default function TrackDetail() {
  const { trackId } = useParams<{ trackId: string }>();
  const navigate = useNavigate();

  const [track, setTrack] = useState<TrackCurriculum | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [progress, setProgress] = useState<LessonProgress[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [isAssignmentsLoading, setIsAssignmentsLoading] = useState(false);
  const [assignmentsError, setAssignmentsError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnrollmentLoading, setIsEnrollmentLoading] = useState(true);
  const [isProgressLoading, setIsProgressLoading] = useState(false);
  const [progressActionLessonId, setProgressActionLessonId] =
    useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);

  const numericTrackId = Number(trackId);
  const isValidTrackId =
    Number.isInteger(numericTrackId) && numericTrackId > 0;

  const currentEnrollment = useMemo(
    () =>
      enrollments.find(
        (enrollment) => enrollment.track_id === numericTrackId,
      ),
    [enrollments, numericTrackId],
  );

  const totalLessons = useMemo(
    () =>
      track?.modules.reduce(
        (total, module) => total + module.lessons.length,
        0,
      ) ?? 0,
    [track],
  );

  const completedLessons = useMemo(
    () =>
      progress.filter(
        (item) => item.status === "completed",
      ).length,
    [progress],
  );

  const overallProgress =
    totalLessons > 0
      ? Math.round((completedLessons / totalLessons) * 100)
      : 0;

  const assignmentsByModule = useMemo(
    () => {
      const grouped = new Map<number, Assignment[]>();

      assignments
        .filter((assignment) => assignment.is_active)
        .forEach((assignment) => {
          if (assignment.module_id === null) {
            return;
          }

          const current = grouped.get(assignment.module_id) ?? [];
          current.push(assignment);
          grouped.set(assignment.module_id, current);
        });

      grouped.forEach((items) => {
        items.sort((a, b) => a.ordering - b.ordering || a.id - b.id);
      });

      return grouped;
    },
    [assignments],
  );

  const progressByLesson = useMemo(
    () =>
      new Map(
        progress.map((item) => [item.lesson_id, item]),
      ),
    [progress],
  );

  const loadCurriculum = useCallback(async () => {
    if (!isValidTrackId) {
      setError("The requested track ID is invalid.");
      setIsLoading(false);
      setIsEnrollmentLoading(false);
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

  const loadEnrollment = useCallback(async () => {
    if (!isValidTrackId) {
      return;
    }

    setIsEnrollmentLoading(true);

    try {
      const data = await enrollmentService.getMyEnrollments();
      setEnrollments(data);
    } catch (requestError) {
      console.error("Failed to load enrollment status", requestError);
      setEnrollments([]);
    } finally {
      setIsEnrollmentLoading(false);
    }
  }, [isValidTrackId]);

  const loadAssignments = useCallback(async () => {
    if (
      !isValidTrackId ||
      !currentEnrollment ||
      currentEnrollment.status === "cancelled"
    ) {
      setAssignments([]);
      setAssignmentsError(null);
      return;
    }

    setIsAssignmentsLoading(true);
    setAssignmentsError(null);

    try {
      const data = await assignmentService.getByTrack(numericTrackId);
      setAssignments(data);
    } catch (requestError) {
      console.error("Failed to load assignments", requestError);
      setAssignments([]);
      setAssignmentsError("Unable to load assignments right now.");
    } finally {
      setIsAssignmentsLoading(false);
    }
  }, [currentEnrollment, isValidTrackId, numericTrackId]);

  const loadProgress = useCallback(async (enrollmentId: number) => {
    setIsProgressLoading(true);
    setProgressError(null);

    try {
      const data = await enrollmentService.getProgress(enrollmentId);
      setProgress(data);
    } catch (requestError) {
      console.error("Failed to load lesson progress", requestError);
      setProgress([]);
      setProgressError(
        "Unable to load lesson progress. Please try again.",
      );
    } finally {
      setIsProgressLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCurriculum();
    void loadEnrollment();
  }, [loadCurriculum, loadEnrollment]);

  useEffect(() => {
    if (
      currentEnrollment &&
      currentEnrollment.status !== "cancelled"
    ) {
      void loadProgress(currentEnrollment.id);
      void loadAssignments();
    } else {
      setProgress([]);
      setProgressError(null);
      setAssignments([]);
      setAssignmentsError(null);
    }
  }, [currentEnrollment, loadAssignments, loadProgress]);

  const handleEnrollmentCreated = (enrollment: Enrollment) => {
    setEnrollments((current) => [
      ...current.filter(
        (item) => item.track_id !== enrollment.track_id,
      ),
      enrollment,
    ]);
  };

  const handleProgressAction = async (lessonId: number) => {
    if (!currentEnrollment) {
      return;
    }

    const existing = progressByLesson.get(lessonId);

    setProgressActionLessonId(lessonId);
    setProgressError(null);

    try {
      if (!existing) {
        const created = await enrollmentService.createProgress(
          currentEnrollment.id,
          {
            lesson_id: lessonId,
            status: "in_progress",
            progress_percentage: 0,
          },
        );

        setProgress((current) => [...current, created]);
        return;
      }

      const nextStatus: ProgressStatus =
        existing.status === "completed"
          ? "in_progress"
          : "completed";

      const nextPercentage =
        nextStatus === "completed"
          ? 100
          : 0;

      const updated = await enrollmentService.updateProgress(
        currentEnrollment.id,
        existing.id,
        {
          status: nextStatus,
          progress_percentage: nextPercentage,
        },
      );

      setProgress((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item,
        ),
      );
    } catch (requestError) {
      console.error("Failed to update lesson progress", requestError);
      setProgressError(
        "Unable to update this lesson progress. Please try again.",
      );
    } finally {
      setProgressActionLessonId(null);
    }
  };

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
                      (total, module) =>
                        total + module.resources.length,
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

        {!isEnrollmentLoading && (
          <EnrollmentPanel
            trackId={numericTrackId}
            enrollment={currentEnrollment}
            onEnrollmentCreated={handleEnrollmentCreated}
          />
        )}

        {!isEnrollmentLoading &&
          currentEnrollment &&
          currentEnrollment.status !== "cancelled" && (
            <Card className="border-blue-200 shadow-sm">
              <CardContent className="p-5 md:p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">
                      Overall progress
                    </p>

                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {overallProgress}%
                    </p>
                  </div>

                  <div className="sm:min-w-[280px]">
                    <div className="mb-2 flex items-center justify-between text-xs text-gray-500">
                      <span>
                        {completedLessons} of {totalLessons} lessons completed
                      </span>
                      {isProgressLoading && (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      )}
                    </div>

                    <div
                      className="h-2.5 overflow-hidden rounded-full bg-gray-100"
                      aria-label={`Overall progress ${overallProgress}%`}
                    >
                      <div
                        className="h-full rounded-full bg-blue-600 transition-all duration-300"
                        style={{ width: `${overallProgress}%` }}
                      />
                    </div>
                  </div>
                </div>

                {progressError && (
                  <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    <span>{progressError}</span>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="shrink-0"
                      onClick={() =>
                        void loadProgress(currentEnrollment.id)
                      }
                    >
                      Retry
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

        <section className="space-y-5">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Curriculum
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Follow the modules, lessons, assignments, and supporting resources in order.
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
                        {module.description ||
                          "Module description unavailable."}
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
                        {module.lessons.map((lesson, lessonIndex) => {
                          const lessonProgress =
                            progressByLesson.get(lesson.id);

                          const status =
                            lessonProgress?.status ?? "not_started";

                          const isActionLoading =
                            progressActionLessonId === lesson.id;

                          return (
                            <div
                              key={lesson.id}
                              className={`rounded-xl border p-4 transition-colors ${
                                status === "completed"
                                  ? "border-emerald-200 bg-emerald-50/30"
                                  : status === "in_progress"
                                    ? "border-amber-200 bg-amber-50/30"
                                    : "border-gray-200 bg-white"
                              }`}
                            >
                              <div className="flex gap-3">
                                <div
                                  className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                                    status === "completed"
                                      ? "bg-emerald-100 text-emerald-700"
                                      : status === "in_progress"
                                        ? "bg-amber-100 text-amber-700"
                                        : "bg-slate-100 text-slate-600"
                                  }`}
                                >
                                  {status === "completed" ? (
                                    <Check className="h-4 w-4" />
                                  ) : (
                                    lessonIndex + 1
                                  )}
                                </div>

                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                                    <div>
                                      <div className="flex flex-wrap items-center gap-2">
                                        <h4 className="font-semibold text-slate-900">
                                          {lesson.title}
                                        </h4>

                                        <span
                                          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                                            status === "completed"
                                              ? "bg-emerald-100 text-emerald-700"
                                              : status === "in_progress"
                                                ? "bg-amber-100 text-amber-700"
                                                : "bg-slate-100 text-slate-600"
                                          }`}
                                        >
                                          {getProgressLabel(status)}
                                        </span>
                                      </div>

                                      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-600">
                                        {lesson.content ||
                                          "No lesson content available."}
                                      </p>

                                      {lessonProgress && (
                                        <div className="mt-3 max-w-md">
                                          <div className="mb-1 flex justify-between text-xs text-gray-400">
                                            <span>Lesson progress</span>
                                            <span>
                                              {lessonProgress.progress_percentage}%
                                            </span>
                                          </div>

                                          <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
                                            <div
                                              className={`h-full rounded-full transition-all ${
                                                status === "completed"
                                                  ? "bg-emerald-600"
                                                  : "bg-blue-600"
                                              }`}
                                              style={{
                                                width: `${lessonProgress.progress_percentage}%`,
                                              }}
                                            />
                                          </div>
                                        </div>
                                      )}
                                    </div>

                                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                                      {lesson.video_url && (
                                        <a
                                          href={lesson.video_url}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700"
                                        >
                                          <PlayCircle className="h-4 w-4" />
                                          Video
                                          <ExternalLink className="h-3.5 w-3.5" />
                                        </a>
                                      )}

                                      {currentEnrollment && (
                                        <Button
                                          type="button"
                                          size="sm"
                                          variant={
                                            status === "completed"
                                              ? "outline"
                                              : "default"
                                          }
                                          disabled={isActionLoading}
                                          onClick={() =>
                                            void handleProgressAction(
                                              lesson.id,
                                            )
                                          }
                                          className={
                                            status === "completed"
                                              ? "border-amber-200 text-amber-700 hover:bg-amber-50"
                                              : status === "in_progress"
                                                ? "bg-emerald-600 text-white hover:bg-emerald-700"
                                                : "bg-blue-600 text-white hover:bg-blue-700"
                                          }
                                        >
                                          {isActionLoading ? (
                                            <>
                                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                              Saving...
                                            </>
                                          ) : status === "completed" ? (
                                            <>
                                              <Circle className="mr-2 h-4 w-4" />
                                              Reopen
                                            </>
                                          ) : status === "in_progress" ? (
                                            <>
                                              <CheckCircle2 className="mr-2 h-4 w-4" />
                                              Complete
                                            </>
                                          ) : (
                                            <>
                                              <PlayCircle className="mr-2 h-4 w-4" />
                                              Start lesson
                                            </>
                                          )}
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  <AssignmentList
                    assignments={assignmentsByModule.get(module.id) ?? []}
                    lessons={module.lessons}
                    isLoading={isAssignmentsLoading}
                    error={assignmentsError}
                  />

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
