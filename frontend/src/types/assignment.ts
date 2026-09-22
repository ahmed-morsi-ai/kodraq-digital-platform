export type AssignmentDifficulty =
  | "beginner"
  | "intermediate"
  | "advanced";

export interface Assignment {
  id: number;
  track_id: number | null;
  module_id: number | null;
  lesson_id: number | null;
  title: string;
  description: string;
  instructions: string;
  difficulty: AssignmentDifficulty;
  ordering: number;
  is_mandatory: boolean;
  is_active: boolean;
  due_days: number | null;
  estimated_minutes: number | null;
  evaluation_config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}
