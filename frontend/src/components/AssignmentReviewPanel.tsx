import { useId, useRef, useState } from "react";
import ReviewFields from "@/components/ReviewFields";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { statusLabel, submissionError } from "@/lib/submissions";
import { submissionService } from "@/services/submission.service";
import type { ReviewStatus, SubmissionDetail } from "@/types/submission";

export default function AssignmentReviewPanel({ submission, busy, onBusy, onReviewed }: {
  submission: SubmissionDetail;
  busy: boolean;
  onBusy: (value: boolean) => void;
  onReviewed: (id: number, message: string) => void;
}) {
  const id = useId();
  const pending = useRef(false);
  const [decision, setDecision] = useState<ReviewStatus>("CHANGES_REQUIRED");
  const [grade, setGrade] = useState("");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState<string | null>(null);
  const decisions: ReviewStatus[] = ["CHANGES_REQUIRED", "APPROVED", "REJECTED"];
  if (submission.status === "SUBMITTED") decisions.unshift("UNDER_REVIEW");
  async function review() {
    if (pending.current || busy || !feedback.trim()) return;
    pending.current = true;
    onBusy(true);
    setError(null);
    try {
      await submissionService.review(submission.id, { feedback_text: feedback.trim(), grade: grade === "" ? null : Number(grade), status_transition: decision });
      onReviewed(submission.id, "Review saved and shared with the student.");
    } catch (requestError) { setError(submissionError(requestError)); }
    finally { pending.current = false; onBusy(false); }
  }
  return <form className="space-y-4 rounded-xl border bg-slate-50 p-4" onSubmit={(event) => { event.preventDefault(); void review(); }}>
    <h4 className="font-semibold">Instructor review</h4>
    <div className="space-y-2">
      <Label htmlFor={`${id}-decision`}>Decision</Label>
      <select id={`${id}-decision`} value={decision} disabled={busy} onChange={(event) => setDecision(event.target.value as ReviewStatus)} className="w-full rounded-md border bg-white p-2 text-sm capitalize">
        {decisions.map((value) => <option value={value} key={value}>{statusLabel(value)}</option>)}
      </select>
    </div>
    <ReviewFields grade={grade} feedback={feedback} onGradeChange={setGrade} onFeedbackChange={setFeedback} disabled={busy} />
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <Button type="submit" disabled={busy || !feedback.trim()}>{busy ? "Saving…" : "Save review"}</Button>
  </form>;
}
