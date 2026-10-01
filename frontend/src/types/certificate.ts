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
