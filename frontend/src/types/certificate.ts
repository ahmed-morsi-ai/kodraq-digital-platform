export type CertificateStatus = "ISSUED" | "REVOKED";

export interface Certificate {
  id: number;
  student_id: number;
  track_id: number;
  graduation_result_id: number;
  certificate_number: string;
  final_score: number | null;
  status: CertificateStatus | string;
  file_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificateVerification {
  valid: boolean;
  certificate_number: string;
  student_name: string;
  track_name: string;
  issue_date: string;
  status?: string;
  final_score?: number | null;
}

export interface GraduationGateCheck {
  id: number;
  evaluation_id: number;
  gate_key: string;
  passed: boolean;
  actual_value: number | null;
  required_value: number | null;
  failure_reason: string | null;
  details: Record<string, unknown> | null;
}

export interface GraduationEvaluation {
  id: number;
  user_id: number;
  track_id: number;
  overall_score: number | null;
  is_eligible: boolean;
  status: string;
  evaluated_at: string | null;
  created_at: string;
  updated_at: string;
  gate_checks: GraduationGateCheck[];
}
