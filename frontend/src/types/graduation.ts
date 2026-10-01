export type GraduationStatus = "PENDING" | "ELIGIBLE" | "GRADUATED" | "NOT_GRADUATED";

export interface GraduationGate {
  gate_key: string;
  passed: boolean;
  actual_value: number;
  required_value: number;
  failure_reason: string | null;
  details: Record<string, unknown>;
}

export interface GraduationCheck {
  id: number;
  rule_id: number;
  gate_key: string;
  passed: boolean;
  score: number | null;
  required_value: number | null;
  failure_reason: string | null;
  details: Record<string, unknown> | null;
}

export interface GraduationResult {
  id: number;
  student_id: number;
  track_id: number;
  overall_score: number | null;
  eligible: boolean;
  status: GraduationStatus;
  evaluated_at: string | null;
  finalized_at: string | null;
  finalized_by: number | null;
  checks: GraduationCheck[];
  created_at: string;
  updated_at: string;
}

export interface GraduationEligibility {
  user_id: number;
  track_id: number;
  overall_score: number;
  is_eligible: boolean;
  status: GraduationStatus;
  evaluated_at: string;
  gate_checks: GraduationGate[];
  finalized_result: GraduationResult | null;
}
