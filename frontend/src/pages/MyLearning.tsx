import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  ChevronRight,
  GraduationCap,
  Layers3,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { enrollmentService } from "@/services/enrollment.service";
import { trackService } from "@/services/track.service";
import type {
  Enrollment,
  EnrollmentDetail,
} from "@/types/enrollment";
import type { TrackCurriculum } from "@/types/track";
import type { LessonProgress } from "@/types/progress";

interface EnrollmentStats {
  totalLessons: number;
  completedLessons: number;
  loading: boolean;
}

interface EnrolledTrackData {
  enrollment: Enrollment;
  track: TrackCurriculum;
  totalLessons: number;
  completedLessons: number;
  progressPercentage: number;
  isStatsLoading: boolean;
}

export default function MyLearning() {
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [tracks, setTracks] = useState<TrackCurriculum[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statsMap, setStatsMap] = useState<
    Record<number, EnrollmentStats>
  >({});

  const loadLearning = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const enrollmentsData = await enrollmentService.getMyEnrollments();

      const activeEnrollments = enrollmentsData.filter(
        (enrollment: Enrollment) => enrollment.status !== "cancelled",
      );

      setEnrollments(activeEnrollments);

      const initialStats: Record<number, EnrollmentStats> = {};

      activeEnrollments.forEach((enrollment: Enrollment) => {
        initialStats[enrollment.id] = {
          totalLessons: 0,
          completedLessons: 0,
          loading: true,
        };
      });

      setStatsMap(initialStats);

      const detailResults = await Promise.all(
        activeEnrollments.map(
          async (enrollment: Enrollment): Promise<{
            enrollment: Enrollment;
            detail: EnrollmentDetail;
          }> => {
            const detail = await enrollmentService.getEnrollment(
              enrollment.id,
            );

            return {
              enrollment,
              detail,
            };
          },
        ),
      );

      const trackResults = await Promise.all(
        detailResults
          .filter(({ detail }) => detail.track)
          .map(async ({ enrollment, detail }) => {
            const trackId = detail.track?.id;

            if (!trackId) {
              return null;
            }

            const [curriculum, progress] = await Promise.all([
              trackService.getCurriculum(trackId),
              enrollmentService.getProgress(enrollment.id),
            ]);

            return {
              enrollment,
              track: curriculum,
              progress,
            };
          }),
      );

      const validResults = trackResults.filter(
        (
          result,
        ): result is {
          enrollment: Enrollment;
          track: TrackCurriculum;
          progress: LessonProgress[];
        } => result !== null,
      );

      setTracks(validResults.map((result) => result.track));

      const nextStats: Record<number, EnrollmentStats> = {};

      validResults.forEach(({ enrollment, track, progress }) => {
        const totalLessons = track.modules.reduce(
          (sum, module) => sum + module.lessons.length,
          0,
        );

        const completedLessons = progress.filter(
          (item) => item.status === "completed",
        ).length;

        nextStats[enrollment.id] = {
          totalLessons,
          completedLessons,
          loading: false,
        };
      });

      activeEnrollments.forEach((enrollment: Enrollment) => {
        if (!nextStats[enrollment.id]) {
          nextStats[enrollment.id] = {
            totalLessons: 0,
            completedLessons: 0,
            loading: false,
          };
        }
      });

      setStatsMap(nextStats);
    } catch (requestError) {
      console.error("Failed to load learning data", requestError);
      setError(
        "Unable to load your enrollments. Please try again later.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLearning();
  }, [loadLearning]);

  const enrolledTracksData = useMemo(() => {
    return enrollments
      .map((enrollment) => {
        const track = tracks.find(
          (item) => item.id === enrollment.track_id,
        );

        if (!track) {
          return null;
        }

        const stats = statsMap[enrollment.id];
        const isStatsLoading = !stats || stats.loading;
        const totalLessons = stats?.totalLessons ?? 0;
        const completedLessons = stats?.completedLessons ?? 0;

        const progressPercentage =
          totalLessons > 0
            ? Math.round((completedLessons / totalLessons) * 100)
            : 0;

        return {
          enrollment,
          track,
          totalLessons,
          completedLessons,
          progressPercentage,
          isStatsLoading,
        };
      })
      .filter(
        (item): item is EnrolledTrackData => item !== null,
      );
  }, [enrollments, tracks, statsMap]);

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-81px)] w-full items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>

          <h2 className="mt-5 text-lg font-semibold text-slate-900">
            Loading your learning paths
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Retrieving your enrolled tracks and progress...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full px-6 py-10">
        <div className="mx-auto max-w-3xl">
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-14 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600">
                <BookOpen className="h-7 w-7" />
              </div>

              <h2 className="mt-5 text-xl font-semibold text-red-900">
                Something went wrong
              </h2>

              <p className="mt-2 max-w-lg text-sm leading-6 text-red-700">
                {error}
              </p>

              <Button
                type="button"
                className="mt-6 gap-2 bg-blue-600 text-white hover:bg-blue-700"
                onClick={() => void loadLearning()}
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-6 py-8 md:py-12">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
              My Learning
            </h1>

            <p className="mt-2 text-sm text-gray-500 md:text-base">
              Pick up where you left off and track your progress.
            </p>
          </div>

          <Button
            asChild
            className="gap-2 bg-blue-600 text-white hover:bg-blue-700"
          >
            <Link to="/tracks">
              <Layers3 className="h-4 w-4" />
              Browse more tracks
            </Link>
          </Button>
        </div>

        {enrolledTracksData.length === 0 ? (
          <Card className="border-gray-200 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-50 text-gray-400">
                <GraduationCap className="h-8 w-8" />
              </div>

              <h3 className="mt-5 text-xl font-semibold text-slate-900">
                No enrollments yet
              </h3>

              <p className="mt-2 max-w-md text-sm leading-6 text-gray-500">
                You haven&apos;t enrolled in any learning tracks yet.
                Explore our curriculum and start your learning journey today.
              </p>

              <Button
                asChild
                className="mt-6 gap-2 bg-blue-600 text-white hover:bg-blue-700"
              >
                <Link to="/tracks">Explore tracks</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {enrolledTracksData.map((data) => (
              <Card
                key={data.enrollment.id}
                className="flex h-full flex-col overflow-hidden border-gray-200 shadow-sm transition-all hover:border-blue-200 hover:shadow-md"
              >
                <CardHeader className="flex-1 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                      <BookOpen className="h-6 w-6" />
                    </div>

                    <span className="inline-flex shrink-0 items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                      Enrolled
                    </span>
                  </div>

                  <div>
                    <CardTitle className="line-clamp-2 text-lg font-bold leading-tight text-slate-900">
                      {data.track.name}
                    </CardTitle>

                    <CardDescription className="mt-2 line-clamp-2 text-sm text-gray-500">
                      {data.track.description ||
                        "Continue your enrolled learning track."}
                    </CardDescription>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 pb-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-700">
                        Course Progress
                      </span>

                      {data.isStatsLoading ? (
                        <Loader2 className="h-3 w-3 animate-spin text-gray-400" />
                      ) : (
                        <span className="font-medium text-blue-600">
                          {data.progressPercentage}%
                        </span>
                      )}
                    </div>

                    <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full bg-blue-600 transition-all duration-500 ease-in-out"
                        style={{
                          width: `${data.progressPercentage}%`,
                        }}
                      />
                    </div>

                    {!data.isStatsLoading &&
                      data.totalLessons > 0 && (
                        <p className="text-[11px] text-gray-500">
                          {data.completedLessons} of {data.totalLessons}{" "}
                          lessons completed
                        </p>
                      )}
                  </div>
                </CardContent>

                <CardFooter className="flex flex-col gap-2 pt-0 sm:flex-row">
                  <Button
                    asChild
                    variant="ghost"
                    className="w-full justify-between bg-gray-50 hover:bg-blue-50 hover:text-blue-700"
                  >
                    <Link to={`/tracks/${data.track.id}`}>
                      {data.progressPercentage > 0
                        ? "Continue learning"
                        : "Start learning"}
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </Button>

                  <Button
                    asChild
                    variant="outline"
                    className="w-full justify-center border-blue-200 text-blue-700 hover:bg-blue-50"
                  >
                    <Link to={`/tracks/${data.track.id}/final-project`}>
                      Final project
                    </Link>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

