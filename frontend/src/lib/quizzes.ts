import { isAxiosError } from "axios";
import type { User } from "@/types/auth";
import type { QuizAttemptSubmit, StudentQuizQuestion } from "@/types/quiz";

export function canTakeQuiz(user: User | null): boolean {
  const role = user?.role_name?.toLowerCase() ?? user?.role?.toLowerCase();
  return Boolean(user?.is_active && !user.is_superuser && (!role || role === "student"));
}

export function quizError(error: unknown): string {
  if (isAxiosError<{ detail?: string | { msg: string }[] }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join(". ");
  }
  return "Unable to complete the request. Check your connection and try again.";
}

export function remainingQuizSeconds(deadline: string | null, now = Date.now()): number | null {
  return deadline === null ? null : Math.max(0, Math.ceil((Date.parse(deadline) - now) / 1000));
}

export function formatQuizTime(seconds: number): string {
  const value = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

export function formatQuizScore(percentage: number): string {
  return `${percentage.toLocaleString("en-US", { maximumFractionDigits: 2 })}%`;
}

export function quizPayload(questions: StudentQuizQuestion[], answers: Record<number, number | null>, flagReason: string | null = null): QuizAttemptSubmit {
  return {
    answers: questions.map(({ question_id }) => ({ question_id, selected_option_id: answers[question_id] ?? null })),
    is_flagged: flagReason !== null,
    flag_reason: flagReason,
  };
}
