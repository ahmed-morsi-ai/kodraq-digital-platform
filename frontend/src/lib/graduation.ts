import { isAxiosError } from "axios";
import type { User } from "@/types/auth";
import type { GraduationEligibility, GraduationStatus } from "@/types/graduation";

export function graduationRole(user: User | null): "student" | "manager" | null {
  if (!user?.is_active) return null;
  const role = (user.role_name ?? user.role)?.toLowerCase();
  if (user.is_superuser || role === "admin" || role === "instructor") return "manager";
  return !role || role === "student" ? "student" : null;
}

export function canFinalizeGraduation(user: User | null, eligibility: GraduationEligibility): boolean {
  return graduationRole(user) === "manager"
    && String(user?.id) !== String(eligibility.user_id)
    && eligibility.is_eligible && eligibility.status === "ELIGIBLE";
}

export function studentIdInput(value: string): number | null {
  if (!/^[1-9]\d*$/.test(value.trim())) return null;
  const id = Number(value.trim());
  return Number.isSafeInteger(id) ? id : null;
}

export const graduationStatus: Record<GraduationStatus, string> = {
  PENDING: "Pending evaluation", ELIGIBLE: "Eligible - awaiting finalization",
  GRADUATED: "Graduated", NOT_GRADUATED: "Not graduated",
};

export const graduationGates: Record<string, { title: string; description: string }> = {
  enrollment: { title: "Active enrollment", description: "The student, enrollment, and track must all be active." },
  curriculum_completion: { title: "Curriculum completion", description: "Complete every lesson with 100% progress." },
  mandatory_assignments: { title: "Mandatory assignments", description: "Every active mandatory assignment must be approved." },
  quiz_average: { title: "Quiz average", description: "Pass every active quiz. The average of the best completed scores must meet the required minimum." },
  final_project_score: { title: "Final project", description: "An instructor must approve the final project with a passing grade." },
  overall_score: { title: "Overall score", description: "Curriculum, assignments, quizzes, and final project each contribute 25%. Every gate must still pass." },
};

export function graduationError(error: unknown): string {
  if (isAxiosError<{ detail?: string | { msg: string }[] }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) return detail.map((item) => item.msg).join(". ");
    if (error.response?.status === 403) return "You do not have access to this student's graduation in this track.";
    if (error.response?.status === 404) return "The student, track, or graduation record was not found.";
    if (error.response?.status === 409) return "Eligibility has changed. Refresh the current gates before continuing.";
  }
  return "Unable to load graduation data. Check your connection and try again.";
}
