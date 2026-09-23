export type ProjectSubmissionStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "CHANGES_REQUIRED"
  | "APPROVED"
  | "REJECTED";

export interface ProjectRequirement {
  id: number;
  project_id: number;
  description: string;
  is_mandatory: boolean;
  order: number;
}

export interface TrainingProject {
  id: number;
  track_id: number;
  title: string;
  description: string | null;
  passing_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  requirements: ProjectRequirement[];
}

export interface ProjectReview {
  id: number;
  submission_id: number;
  reviewer_id: number;
  score: number | null;
  feedback: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectSubmission {
  id: number;
  project_id: number;
  student_id: number;
  github_url: string | null;
  live_url: string | null;
  file_url: string | null;
  student_notes: string | null;
  status: ProjectSubmissionStatus;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
  reviews: ProjectReview[];
}

export interface ProjectSubmissionCreate {
  github_url?: string | null;
  live_url?: string | null;
  file_url?: string | null;
  student_notes?: string | null;
}

export interface ProjectSubmissionUpdate extends ProjectSubmissionCreate {
  status?: "SUBMITTED";
}

export interface ProjectReviewCreate {
  score: number;
  feedback: string;
}
