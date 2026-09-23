import { useState } from "react";

import { useAuth } from "@/context/AuthContext";


import { isAxiosError } from "axios";
import {
  CheckCircle2,
  Loader2,
  MessageSquareText,
  Star,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { finalProjectService } from "@/services/finalProject.service";
import type {
  ProjectSubmission,
  TrainingProject,
} from "@/types/finalProject";

interface InstructorReviewPanelProps {
  project: TrainingProject;
  submissions: ProjectSubmission[];
  onReviewed: () => Promise<void>;
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (error.response?.status === 403) {
      return "You are not assigned to review this track.";
    }
  }

  return "Unable to submit the review right now.";
}

function ReviewEditor({
  project,
  submission,
  onReviewed,
}: {
  project: TrainingProject;
  submission: ProjectSubmission;
  onReviewed: () => Promise<void>;
}) {
  const latestReview =
    submission.reviews.length > 0
      ? submission.reviews[submission.reviews.length - 1]
      : null;

  const [score, setScore] = useState(
    latestReview?.score ?? project.passing_score,
  );
  const [feedback, setFeedback] = useState(
    latestReview?.feedback ?? "",
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleReview = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await finalProjectService.createReview(submission.id, {
        score: Math.min(100, Math.max(0, score)),
        feedback: feedback.trim(),
      });

      setSuccess(true);
      await onReviewed();
    } catch (requestError) {
      console.error("Failed to create final project review", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mt-5 space-y-4 rounded-xl border border-gray-200 bg-gray-50/80 p-4">
      <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
        <div className="space-y-2">
          <Label htmlFor={`score-${submission.id}`}>Score</Label>
          <Input
            id={`score-${submission.id}`}
            type="number"
            min={0}
            max={100}
            value={score}
            onChange={(event) =>
              setScore(Number(event.target.value))
            }
          />
          <p className="text-xs text-gray-400">
            Passing score: {project.passing_score}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor={`feedback-${submission.id}`}>Feedback</Label>
          <textarea
            id={`feedback-${submission.id}`}
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            rows={4}
            placeholder="Explain the decision and required improvements."
            className="w-full rounded-md border border-input bg-white px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          Review submitted and submission status updated.
        </div>
      )}

      <div className="flex justify-end">
        <Button
          type="button"
          disabled={isSaving || !feedback.trim()}
          onClick={() => void handleReview()}
          className="gap-2 bg-slate-900 text-white hover:bg-slate-800"
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <MessageSquareText className="h-4 w-4" />
          )}
          Save review
        </Button>
      </div>
    </div>
  );
}

export default function InstructorReviewPanel({
  project,
  submissions,
  onReviewed,
}: InstructorReviewPanelProps) {
  const { user } = useAuth();
  const [selectedSubmissionId, setSelectedSubmissionId] =
    useState<number | null>(null);

  const roleName = user?.role_name?.toLowerCase() ?? "";
  const canReview =
    user !== null &&
    (user.is_superuser ||
      roleName === "admin" ||
      roleName === "instructor");

  if (!canReview) {
    return null;
  }

  const selected =
    submissions.find(
      (submission) => submission.id === selectedSubmissionId,
    ) ?? submissions[0] ?? null;

  return (
    <Card className="border-slate-700 bg-slate-950 text-slate-100 shadow-sm">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-white">
            <Star className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-xl text-white">
              Instructor review
            </CardTitle>
            <CardDescription className="mt-2 text-white/50">
              Review submitted projects and let the backend state machine set
              APPROVED or CHANGES_REQUIRED from the score.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {submissions.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-8 text-center text-sm text-white/50">
            No student submissions are available for review yet.
          </div>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              {submissions.map((submission) => (
                <button
                  key={submission.id}
                  type="button"
                  onClick={() => setSelectedSubmissionId(submission.id)}
                  className={`rounded-xl border p-4 text-left transition ${
                    selected?.id === submission.id
                      ? "border-emerald-300/50 bg-emerald-300/10"
                      : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-white">
                      Student #{submission.student_id}
                    </span>

                    <span className="rounded-full bg-white/10 px-2 py-1 text-[11px] font-semibold text-white/70">
                      {submission.status}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-white/40">
                    Submission #{submission.id}
                  </p>
                </button>
              ))}
            </div>

            {selected &&
              (selected.status === "SUBMITTED" ||
                selected.status === "UNDER_REVIEW") && (
                <ReviewEditor
                  key={selected.id}
                  project={project}
                  submission={selected}
                  onReviewed={onReviewed}
                />
              )}

            {selected &&
              selected.status !== "SUBMITTED" &&
              selected.status !== "UNDER_REVIEW" && (
                <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/60">
                  This submission is currently <strong>{selected.status}</strong>
                  . A new instructor review is available only for submitted
                  work.
                </div>
              )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
