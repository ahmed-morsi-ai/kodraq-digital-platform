import { useId, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import ProjectSubmissionDetails, { ProjectStatusBadge } from "@/components/ProjectSubmissionDetails";
import ReviewFields from "@/components/ReviewFields";
import { canReviewProject, projectError, projectReviewPayload, projectRole } from "@/lib/finalProjects";
import { finalProjectService, reviewProjectSubmission } from "@/services/finalProject.service";
import type { User } from "@/types/auth";
import type { ProjectReviewDecision, ProjectSubmission, TrainingProject } from "@/types/finalProject";

function ReviewEditor({ project, submission, onUpdated, onBusy }: {
  project: TrainingProject;
  submission: ProjectSubmission;
  onUpdated: (submission: ProjectSubmission) => void;
  onBusy: (busy: boolean) => void;
}) {
  const id = useId();
  const pending = useRef(false);
  const [decision, setDecision] = useState<ProjectReviewDecision>("CHANGES_REQUIRED");
  const [score, setScore] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (pending.current) return;
    let payload;
    try {
      payload = projectReviewPayload(decision, score, feedback, project.passing_score);
    } catch (validationError) {
      setError(validationError instanceof Error ? validationError.message : "Check the review fields.");
      return;
    }
    pending.current = true;
    setBusy(true);
    onBusy(true);
    setError(null);
    try {
      onUpdated(await reviewProjectSubmission(submission, payload));
    } catch (requestError) {
      setError(projectError(requestError));
      try {
        onUpdated(await finalProjectService.getSubmission(submission.id));
      } catch {
        // A failed refresh must not hide the original review error or discard the form.
      }
    } finally {
      pending.current = false;
      setBusy(false);
      onBusy(false);
    }
  }

  return <form noValidate onSubmit={(event) => { event.preventDefault(); void save(); }} className="mt-6 space-y-4 border-t border-slate-200 pt-6" aria-label="Review final project" aria-busy={busy}>
    <h3 className="font-semibold text-slate-900">New review</h3>
    <div className="space-y-2">
      <Label htmlFor={`${id}-decision`}>Review decision</Label>
      <select id={`${id}-decision`} value={decision} onChange={(event) => setDecision(event.target.value as ProjectReviewDecision)} disabled={busy} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500">
        {submission.status === "SUBMITTED" && <option value="UNDER_REVIEW">Start review</option>}
        <option value="CHANGES_REQUIRED">Request changes</option>
        <option value="APPROVED">Approve</option>
        <option value="REJECTED">Reject</option>
      </select>
    </div>
    <ReviewFields grade={score} feedback={feedback} onGradeChange={setScore} onFeedbackChange={setFeedback} disabled={busy} min={0} max={100} hint={decision === "APPROVED" ? `Required: ${project.passing_score}-100 to approve.` : "Optional whole number: 0-100."} />
    {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <p className="text-xs text-slate-500">Approval and rejection close the submission. Request changes to allow the student to resubmit.</p>
    <div className="flex justify-end">
      <Button type="submit" disabled={busy || !feedback.trim()}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Save review</Button>
    </div>
  </form>;
}

export default function InstructorReviewPanel({ user, project, submissions, onUpdated, hasMore, loadingMore, listError, onLoadMore }: {
  user: User | null;
  project: TrainingProject;
  submissions: ProjectSubmission[];
  onUpdated: (submission: ProjectSubmission) => void;
  hasMore: boolean;
  loadingMore: boolean;
  listError: string | null;
  onLoadMore: () => void;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reviewing, setReviewing] = useState(false);
  if (projectRole(user) !== "manager") return null;
  const selected = submissions.find((item) => item.id === selectedId) ?? submissions[0];
  return <Card className="border-slate-200 shadow-sm">
    <CardHeader>
      <CardTitle className="text-xl">Instructor review</CardTitle>
      <CardDescription>Select a student to inspect their work and review history. {submissions.length} submissions loaded.</CardDescription>
    </CardHeader>
    <CardContent className="space-y-6">
      {submissions.length === 0 && <p className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">No student submissions yet.</p>}
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="space-y-3">
          <div className="max-h-[560px] space-y-2 overflow-y-auto" aria-label="Student submissions">
            {submissions.map((submission) => <button key={submission.id} type="button" disabled={reviewing} aria-pressed={selected?.id === submission.id} onClick={() => setSelectedId(submission.id)} className={`w-full space-y-3 rounded-lg border p-4 text-left transition disabled:opacity-60 ${selected?.id === submission.id ? "border-blue-300 bg-blue-50" : "border-slate-200 hover:bg-slate-50"}`}>
              <span className="block text-sm font-semibold text-slate-900">Student #{submission.student_id}</span>
              <ProjectStatusBadge status={submission.status} />
            </button>)}
          </div>
          {listError && <p role="alert" className="text-sm text-red-700">{listError}</p>}
          {hasMore && <Button type="button" variant="outline" className="w-full" disabled={loadingMore || reviewing} onClick={onLoadMore}>{loadingMore ? "Loading..." : listError ? "Retry loading submissions" : "Load more submissions"}</Button>}
        </div>
        {selected && <div className="min-w-0 rounded-xl border border-slate-200 p-4 md:p-6">
          <ProjectSubmissionDetails submission={selected} />
          {canReviewProject(user, selected) ? <ReviewEditor key={`${selected.id}:${selected.status}:${selected.reviews.map((review) => review.id).join(",")}`} project={project} submission={selected} onUpdated={onUpdated} onBusy={setReviewing} /> : (
            <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{String(selected.student_id) === String(user?.id) ? "You cannot review your own submission." : "A new review is available only for submitted work or work under review."}</p>
          )}
        </div>}
      </div>
    </CardContent>
  </Card>;
}
