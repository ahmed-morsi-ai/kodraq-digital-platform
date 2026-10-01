import { isAxiosError } from "axios";
import type { SubmissionDetail, SubmissionStatus } from "@/types/submission";

export function submissionError(error: unknown): string {
  if (isAxiosError<{ detail?: string | { msg: string }[] }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join(". ");
    if (error.response?.status === 403) return "You do not have access to this submission.";
    if (error.response?.status === 404) return "The submission or file is no longer available.";
  }
  return "Unable to complete the request. Check your connection and try again.";
}

export function statusLabel(status: SubmissionStatus): string {
  return status.toLowerCase().replace(/_/g, " ");
}

export function isRepositoryUrl(value: string): boolean {
  const match = /^https:\/\/github\.com\/([a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?)\/([a-z0-9_.-]{1,100})\/?$/i.exec(value);
  return match !== null && match[0] === value && ![".", "..", ".git"].includes(match[2] ?? "");
}

export function submissionTimeline(submission: SubmissionDetail) {
  return [
    { id: "created", date: submission.created_at, label: "Created", feedback: null, grade: null },
    ...submission.attempts.map((attempt) => ({ id: `attempt-${attempt.id}`, date: attempt.submitted_at, label: "Submitted for review", feedback: null, grade: null })),
    ...submission.reviews.map((review) => ({ id: review.id, date: review.created_at, label: statusLabel(review.status_transition), feedback: review.feedback_text, grade: review.grade })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}
