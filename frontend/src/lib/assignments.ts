import { isAxiosError } from "axios";
import type { Assignment } from "../types/assignment";
import type { TrackModule } from "../types/track";

export function assignmentModuleId(assignment: Assignment, modules: TrackModule[]): number | null {
  return assignment.module_id ?? modules.find((module) =>
    module.lessons.some((lesson) => lesson.id === assignment.lesson_id),
  )?.id ?? null;
}

export function assignmentContext(assignment: Assignment, modules: TrackModule[]): string {
  const module = modules.find((item) => item.id === assignmentModuleId(assignment, modules));
  const lesson = module?.lessons.find((item) => item.id === assignment.lesson_id);
  return [module?.title, lesson?.title].filter(Boolean).join(" / ") || "Track assignment";
}

export function assignmentError(error: unknown): string {
  if (isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item: { loc?: unknown[]; msg?: string }) =>
        `${item.loc?.slice(1).join(".") || "Assignment"}: ${item.msg || "Invalid value"}`,
      ).join("; ");
    }
    if (error.response?.status === 403) return "You do not have access to assignments in this track.";
    if (error.response?.status === 404) return "This assignment is no longer available.";
  }
  return "Unable to complete the request. Please try again.";
}
