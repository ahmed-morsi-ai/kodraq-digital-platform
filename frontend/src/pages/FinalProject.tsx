import { useCallback, useEffect, useMemo, useState } from "react";
import { isAxiosError } from "axios";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileArchive,
  GitBranch,
  Globe,
  Loader2,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Star,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import FinalProjectSubmissionForm from "@/components/FinalProjectSubmissionForm";
import InstructorReviewPanel from "@/components/InstructorReviewPanel";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { finalProjectService } from "@/services/finalProject.service";
import type {
  ProjectSubmission,
  ProjectSubmissionCreate,
  TrainingProject,
} from "@/types/finalProject";
import type { User } from "@/types/auth";

function isStaffUser(user: User | null) {
  const roleName = user?.role_name?.toLowerCase() ?? "";

  return Boolean(
    user &&
      (user.is_superuser ||
        roleName === "admin" ||
        roleName === "instructor"),
  );
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (error.response?.status === 404) {
      return "This track does not have an active final project yet.";
    }

    if (error.response?.status === 403) {
      return "You do not have access to this final project.";
    }
  }

  return "Unable to load the final project right now.";
}

function getStatusStyles(status: ProjectSubmission["status"]) {
  switch (status) {
    case "DRAFT":
      return "bg-slate-100 text-slate-700";
    case "SUBMITTED":
      return "bg-blue-50 text-blue-700";
    case "UNDER_REVIEW":
      return "bg-amber-50 text-amber-700";
    case "CHANGES_REQUIRED":
      return "bg-orange-50 text-orange-700";
    case "APPROVED":
      return "bg-emerald-50 text-emerald-700";
    case "REJECTED":
      return "bg-red-50 text-red-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function getStatusLabel(status: ProjectSubmission["status"]) {
  switch (status) {
    case "CHANGES_REQUIRED":
      return "Changes required";
    case "UNDER_REVIEW":
      return "Under review";
    default:
      return status.replace(/_/g, " ");
  }
}

function SubmissionLinks({ submission }: { submission: ProjectSubmission }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {submission.github_url && (
        <a
          href={submission.github_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
        >
          <GitBranch className="h-4 w-4 text-slate-500" />
          GitHub
        </a>
      )}

      {submission.live_url && (
        <a
          href={submission.live_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
        >
          <Globe className="h-4 w-4 text-slate-500" />
          Live project
        </a>
      )}

      {submission.file_url && (
        <a
          href={submission.file_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
        >
          <FileArchive className="h-4 w-4 text-slate-500" />
          Project files
        </a>
      )}
    </div>
  );
}

function ReviewHistory({ submission }: { submission: ProjectSubmission }) {
  if (submission.reviews.length === 0) {
    return null;
  }

  return (
    <Card className="border-gray-200 shadow-sm">
      <CardHeader>
        <CardTitle className="text-xl text-slate-900">
          Instructor feedback
        </CardTitle>
        <CardDescription>
          Review history for this final project.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {[...submission.reviews].reverse().map((review) => (
          <div
            key={review.id}
            className="rounded-xl border border-gray-200 bg-gray-50/70 p-4"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-500" />
                <span className="font-semibold text-slate-900">
                  {review.score !== null
                    ? `${review.score}/100`
                    : "Review"}
                </span>
              </div>

              <span className="text-xs text-gray-400">
                {new Date(review.created_at).toLocaleString()}
              </span>
            </div>

            {review.feedback && (
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-600">
                {review.feedback}
              </p>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function FinalProject() {
  const { trackId } = useParams<{ trackId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const numericTrackId = Number(trackId);
  const validTrackId =
    Number.isInteger(numericTrackId) && numericTrackId > 0;

  const staff = isStaffUser(user);

  const [project, setProject] = useState<TrainingProject | null>(null);
  const [submission, setSubmission] =
    useState<ProjectSubmission | null>(null);
  const [staffSubmissions, setStaffSubmissions] = useState<
    ProjectSubmission[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPage = useCallback(async () => {
    await Promise.resolve();
    if (!validTrackId) {
      setError("The requested track ID is invalid.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const projectData =
        await finalProjectService.getByTrack(numericTrackId);

      setProject(projectData);

      if (staff) {
        const submissions =
          await finalProjectService.getByProject(projectData.id);

        setStaffSubmissions(submissions);
        setSubmission(null);
      } else {
        const submissions =
          await finalProjectService.getMySubmissions();

        setSubmission(
          submissions.find(
            (item) => item.project_id === projectData.id,
          ) ?? null,
        );
        setStaffSubmissions([]);
      }
    } catch (requestError) {
      console.error("Failed to load final project", requestError);
      setProject(null);
      setSubmission(null);
      setStaffSubmissions([]);
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, [numericTrackId, staff, validTrackId]);

  useEffect(() => {
    const runLoadPage = async () => {
      await loadPage();
    };

    void runLoadPage();
  }, [loadPage]);

  const editable =
    !staff &&
    (!submission ||
      submission.status === "DRAFT" ||
      submission.status === "CHANGES_REQUIRED");

  const latestReview = useMemo(() => {
    if (!submission || submission.reviews.length === 0) {
      return null;
    }

    return submission.reviews[submission.reviews.length - 1];
  }, [submission]);

  const handleCreate = async (payload: ProjectSubmissionCreate) => {
    if (!project) {
      throw new Error("Final project is not loaded.");
    }

    const created = await finalProjectService.createSubmission(
      project.id,
      payload,
    );

    setSubmission(created);

    return created;
  };

  const handleUpdate = async (
    submissionId: number,
    payload: ProjectSubmissionCreate,
  ) => {
    const updated = await finalProjectService.updateSubmission(
      submissionId,
      payload,
    );

    setSubmission(updated);

    return updated;
  };

  const handleSubmit = async (
    submissionId: number,
    payload: ProjectSubmissionCreate,
  ) => {
    const updated = await finalProjectService.updateSubmission(
      submissionId,
      {
        ...payload,
        status: "SUBMITTED",
      },
    );

    setSubmission(updated);

    return updated;
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>

          <h2 className="mt-5 text-lg font-semibold text-slate-900">
            Loading final project
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Preparing the requirements and submission workspace...
          </p>
        </div>
      </div>
    );
  }

  if (!project || error) {
    return (
      <div className="w-full px-6 py-10">
        <div className="mx-auto max-w-3xl">
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-14 text-center">
              <ShieldCheck className="h-10 w-10 text-red-500" />

              <h2 className="mt-5 text-xl font-semibold text-red-900">
                Final project unavailable
              </h2>

              <p className="mt-2 max-w-lg text-sm leading-6 text-red-700">
                {error}
              </p>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(-1)}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Go back
                </Button>

                <Button
                  type="button"
                  onClick={() => void loadPage()}
                  className="gap-2 bg-blue-600 text-white hover:bg-blue-700"
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
    <div className="w-full px-6 py-8 md:py-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <Button
          type="button"
          variant="ghost"
          className="gap-2 px-0 text-gray-500 hover:bg-transparent hover:text-slate-900"
          onClick={() => navigate(`/tracks/${project.track_id}`)}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to track
        </Button>

        <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 bg-gradient-to-br from-blue-50 via-white to-white p-6 md:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Final project
                </div>

                <h1 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
                  {project.title}
                </h1>

                <p className="mt-4 text-sm leading-7 text-gray-600 md:text-base">
                  {project.description ||
                    "Complete the final project requirements and submit your work for instructor review."}
                </p>
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 lg:min-w-[220px]">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                  Passing score
                </p>

                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {project.passing_score}/100
                </p>

                <p className="mt-1 text-xs text-gray-500">
                  Score-based approval
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <Card className="border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-xl text-slate-900">
                Project requirements
              </CardTitle>
              <CardDescription>
                Complete the mandatory requirements before submission.
              </CardDescription>
            </CardHeader>

            <CardContent>
              {project.requirements.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-sm text-gray-500">
                  No detailed requirements have been published yet.
                </div>
              ) : (
                <ol className="space-y-3">
                  {project.requirements.map((requirement, index) => (
                    <li
                      key={requirement.id}
                      className="flex gap-3 rounded-xl border border-gray-200 bg-gray-50/70 p-4"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-xs font-bold text-blue-600 ring-1 ring-gray-200">
                        {index + 1}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="text-sm leading-6 text-slate-700">
                          {requirement.description}
                        </p>

                        <span
                          className={`mt-2 inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${
                            requirement.is_mandatory
                              ? "bg-red-50 text-red-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {requirement.is_mandatory
                            ? "Mandatory"
                            : "Recommended"}
                        </span>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>

          {!staff && submission && (
            <Card className="border-gray-200 shadow-sm">
              <CardHeader>
                <CardTitle className="text-xl text-slate-900">
                  Submission status
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                <div
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold capitalize ${getStatusStyles(
                    submission.status,
                  )}`}
                >
                  {submission.status === "APPROVED" ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : submission.status === "UNDER_REVIEW" ? (
                    <Clock3 className="h-3.5 w-3.5" />
                  ) : (
                    <LockKeyhole className="h-3.5 w-3.5" />
                  )}
                  {getStatusLabel(submission.status)}
                </div>

                <p className="text-sm leading-6 text-gray-500">
                  {submission.status === "APPROVED"
                    ? "Your final project has been approved."
                    : submission.status === "SUBMITTED" ||
                        submission.status === "UNDER_REVIEW"
                      ? "Your submission is locked while it is being reviewed."
                      : submission.status === "CHANGES_REQUIRED"
                        ? "Your instructor requested changes. Update the project and resubmit."
                        : "Your submission is still a draft."}
                </p>

                {submission.submitted_at && (
                  <p className="text-xs text-gray-400">
                    Submitted{" "}
                    {new Date(
                      submission.submitted_at,
                    ).toLocaleString()}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </section>

        {!staff && editable && (
          <FinalProjectSubmissionForm
            key={submission?.id ?? "new"}
            projectId={project.id}
            submission={submission}
            onCreate={handleCreate}
            onUpdate={handleUpdate}
            onSubmit={handleSubmit}
          />
        )}

        {!staff && submission && !editable && (
          <Card className="border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl text-slate-900">
                <LockKeyhole className="h-5 w-5 text-slate-500" />
                Submission locked
              </CardTitle>
              <CardDescription>
                Your submitted project cannot be edited while it is under
                review.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              <SubmissionLinks submission={submission} />

              {submission.student_notes && (
                <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Your notes
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-600">
                    {submission.student_notes}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!staff &&
          submission?.status === "APPROVED" &&
          latestReview && (
            <Card className="border-emerald-200 bg-emerald-50/40 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl text-emerald-900">
                  <CheckCircle2 className="h-5 w-5" />
                  Final project approved
                </CardTitle>
                <CardDescription className="text-emerald-800/70">
                  Your instructor&apos;s final score and feedback are below.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
                  <div className="rounded-xl border border-emerald-200 bg-white p-4 text-center">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Final score
                    </p>

                    <p className="mt-2 text-4xl font-black text-emerald-700">
                      {latestReview.score ?? "Ã¢â‚¬â€"}
                    </p>

                    <p className="text-xs text-gray-400">out of 100</p>
                  </div>

                  <div className="rounded-xl border border-emerald-200 bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Instructor feedback
                    </p>

                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-700">
                      {latestReview.feedback ||
                        "Your instructor approved the project without additional feedback."}
                    </p>
                  </div>
                </div>

                <SubmissionLinks submission={submission} />

                <Button
                  asChild
                  variant="outline"
                  className="gap-2 border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50"
                >
                  <Link to="/my-learning">
                    Back to My Learning
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}

        {!staff && submission && submission.status !== "APPROVED" && (
          <ReviewHistory submission={submission} />
        )}

        {staff && (
          <InstructorReviewPanel
            project={project}
            submissions={staffSubmissions}
            onReviewed={loadPage}
          />
        )}
      </div>
    </div>
  );
}
