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

export type AssignmentCreate = Pick<Assignment, "title" | "description" | "instructions" | "difficulty"> &
  Partial<Omit<Assignment, "id" | "created_at" | "updated_at" | "title" | "description" | "instructions" | "difficulty">>;

export type AssignmentUpdate = Partial<AssignmentCreate>;

export interface AssignmentFilters {
  track_id?: number;
  module_id?: number;
  lesson_id?: number;
  skip?: number;
  limit?: number;
}
