export type SubmissionStatus = "DRAFT" | "SUBMITTED" | "UNDER_REVIEW" | "CHANGES_REQUIRED" | "APPROVED" | "REJECTED";
export type ReviewStatus = Exclude<SubmissionStatus, "DRAFT" | "SUBMITTED">;

export interface Submission {
  id: number;
  assignment_id: number;
  user_id: number;
  status: SubmissionStatus;
  grade: number | null;
  content: string | null;
  github_url: string | null;
  file_path_or_url: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubmissionFile {
  id: string;
  submission_id: number;
  file_name: string;
  file_url: string;
  file_type: string;
  file_size_bytes: number | null;
  created_at: string;
}

export interface SubmissionReview {
  id: string;
  submission_id: number;
  reviewer_id: number | null;
  feedback_text: string;
  grade: number | null;
  status_transition: SubmissionStatus;
  created_at: string;
}

export interface SubmissionDetail extends Submission {
  files: SubmissionFile[];
  reviews: SubmissionReview[];
  attempts: { id: number; submitted_at: string }[];
}

export interface SubmissionInput {
  content?: string | null;
  github_url?: string | null;
}

export interface ReviewInput {
  feedback_text: string;
  grade: number | null;
  status_transition: ReviewStatus;
}
