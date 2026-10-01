import { isAxiosError } from "axios";
import type { User } from "@/types/auth";
import type {
  ProjectReviewCreate, ProjectReviewDecision, ProjectSubmission, ProjectSubmissionCreate,
  ProjectSubmissionStatus,
} from "@/types/finalProject";
import { isRepositoryUrl } from "./submissions";

export function projectRole(user: User | null): "student" | "manager" | null {
  if (!user?.is_active) return null;
  const role = (user.role_name ?? user.role)?.toLowerCase();
  if (user.is_superuser || role === "admin" || role === "instructor") return "manager";
  return !role || role === "student" ? "student" : null;
}

export function canEditProject(submission: ProjectSubmission | null): boolean {
  return !submission || submission.status === "DRAFT" || submission.status === "CHANGES_REQUIRED";
}

export function canReviewProject(user: User | null, submission: ProjectSubmission): boolean {
  return projectRole(user) === "manager" && String(submission.student_id) !== String(user?.id)
    && (submission.status === "SUBMITTED" || submission.status === "UNDER_REVIEW");
}

export const projectStatus: Record<ProjectSubmissionStatus, { label: string; style: string; message: string }> = {
  DRAFT: { label: "Draft", style: "bg-slate-100 text-slate-700", message: "Save your progress, then submit your project when it is ready." },
  SUBMITTED: { label: "Submitted", style: "bg-blue-50 text-blue-700", message: "Your project is submitted and awaiting review. Editing is locked." },
  UNDER_REVIEW: { label: "Under review", style: "bg-amber-50 text-amber-800", message: "Your instructor is reviewing this project. Editing is locked." },
  CHANGES_REQUIRED: { label: "Changes required", style: "bg-orange-50 text-orange-800", message: "Read the feedback, update your work, and resubmit for review." },
  APPROVED: { label: "Approved", style: "bg-emerald-50 text-emerald-800", message: "Your final project has been approved. See your grade and feedback below." },
  REJECTED: { label: "Rejected", style: "bg-red-50 text-red-800", message: "Your project was rejected. This submission is closed; read the instructor feedback below." },
};

export function projectError(error: unknown): string {
  if (isAxiosError<{ detail?: string | { msg: string }[] }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) return detail.map((item) => item.msg).join(". ");
    if (error.response?.status === 403) return "You do not have permission to access or change this final project.";
    if (error.response?.status === 404) return "The final project or submission is unavailable.";
    if (error.response?.status === 409) return "A submission already exists. Refresh to load the saved submission.";
  }
  return "Unable to complete the request. Check your connection and try again.";
}

export function isProjectUrl(value: string): boolean {
  if (!/^https?:\/\/[^/?#]/i.test(value) || /[\s\\]/u.test(value) || [...value].some((char) => char.charCodeAt(0) < 32)) return false;
  try {
    const url = new URL(value);
    const authority = value.split("/")[2] ?? "";
    return Boolean(url.hostname) && !authority.includes("@") && !url.username && !url.password && url.port !== "0";
  } catch {
    return false;
  }
}

export function validateProjectLinks(payload: ProjectSubmissionCreate, submit: boolean): string | null {
  const links = [payload.github_url, payload.live_url, payload.file_url];
  if (links.some((link) => link && link.length > 512)) return "Project URLs must be at most 512 characters.";
  if (payload.github_url && !isRepositoryUrl(payload.github_url)) return "Use a GitHub repository URL: https://github.com/owner/repository.";
  if ([payload.live_url, payload.file_url].some((url) => url && !isProjectUrl(url))) {
    return "Use absolute HTTP or HTTPS project links without spaces or credentials.";
  }
  return submit && !links.some(Boolean) ? "Add a GitHub, live-project, or project-file URL before submitting." : null;
}

export function projectReviewPayload(
  decision: ProjectReviewDecision, score: string, feedback: string, passingScore: number,
): ProjectReviewCreate {
  const grade = score.trim() ? Number(score) : null;
  if (!feedback.trim()) throw new Error("Feedback is required for every review.");
  if (grade !== null && (!Number.isInteger(grade) || grade < 0 || grade > 100)) {
    throw new Error("Enter a whole-number grade between 0 and 100.");
  }
  if (decision === "APPROVED" && (grade === null || grade < passingScore)) {
    throw new Error(`Approval requires a grade of at least ${passingScore}/100.`);
  }
  return { status_decision: decision, score: grade, feedback: feedback.trim() };
}
