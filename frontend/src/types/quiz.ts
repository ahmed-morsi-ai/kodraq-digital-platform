export type QuizAttemptStatus = "IN_PROGRESS" | "COMPLETED";

export interface QuizOption {
  id: number;
  question_id: number;
  text: string;
}

export interface StudentQuestion {
  id: number;
  text: string;
  question_type: string;
  points: number;
  options: QuizOption[];
}

export interface StudentQuizQuestion {
  question_id: number;
  ordering: number;
  question: StudentQuestion;
}

export interface StudentQuiz {
  id: number;
  title: string;
  description: string | null;
  track_id: number | null;
  lesson_id: number | null;
  passing_score: number;
  time_limit_minutes: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  questions: StudentQuizQuestion[];
}

export interface QuizAnswerCreate {
  question_id: number;
  selected_option_id: number | null;
}

export interface QuizAnswerResponse extends QuizAnswerCreate {
  id: number;
  attempt_id: number;
  is_correct: boolean;
}

export interface QuizAttemptSubmit {
  answers: QuizAnswerCreate[];
  is_flagged: boolean;
  flag_reason: string | null;
}

export interface QuizAttempt {
  id: number;
  quiz_id: number;
  user_id: number;
  score: number | null;
  passed: boolean;
  is_flagged: boolean;
  flag_reason: string | null;
  status: QuizAttemptStatus;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  answers: QuizAnswerResponse[];
}

export interface QuizResultQuestion {
  question_id: number;
  text: string;
  points: number;
  selected_option_id: number | null;
  selected_option_text: string | null;
  correct_option_ids: number[];
  correct_option_texts: string[];
  is_correct: boolean;
}

export interface QuizResult {
  attempt_id: number;
  quiz_id: number;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  time_taken_seconds: number;
  is_flagged: boolean;
  flag_reason: string | null;
  questions: QuizResultQuestion[];
}
