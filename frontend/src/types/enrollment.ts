import type { Track } from "./track";

export type EnrollmentStatus =
  | "active"
  | "completed"
  | "cancelled";

export type StudentProgressStatus =
  | "not_started"
  | "in_progress"
  | "completed";

export interface StudentProgress {
  id: number;
  enrollment_id: number;
  lesson_id: number;
  status: StudentProgressStatus;
  progress_percentage: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface StudentProgressCreate {
  lesson_id: number;
  status?: StudentProgressStatus;
  progress_percentage?: number;
}

export interface StudentProgressUpdate {
  status?: StudentProgressStatus;
  progress_percentage?: number;
}

export interface StudentProgressDetail extends StudentProgress {
  lesson?: {
    id: number;
    module_id: number;
    title: string;
    content: string;
    video_url: string | null;
    ordering: number;
  } | null;
}

export interface Enrollment {
  id: number;
  user_id: number;
  track_id: number;
  status: EnrollmentStatus;
  enrolled_at: string;
  completed_at: string | null;
}

export interface EnrollmentCreate {
  track_id: number;
}

export interface EnrollmentUpdate {
  status?: EnrollmentStatus;
  completed_at?: string | null;
}

export interface EnrollmentDetail extends Enrollment {
  track?: Track | null;
  progress: StudentProgressDetail[];
}
