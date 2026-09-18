export type ProgressStatus = "not_started" | "in_progress" | "completed";

export interface LessonProgress {
  id: number;
  enrollment_id: number;
  lesson_id: number;
  status: ProgressStatus;
  progress_percentage: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface ProgressCreatePayload {
  lesson_id: number;
  status?: ProgressStatus;
  progress_percentage?: number;
}

export interface ProgressUpdatePayload {
  status?: ProgressStatus;
  progress_percentage?: number;
}
