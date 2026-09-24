export type PaymentStatus =
  | "PENDING_VERIFICATION"
  | "VERIFIED"
  | "REJECTED";

export type PaymentMethod = "VODAFONE_CASH" | "INSTAPAY";

export interface PaymentInstructions {
  vodafone_cash: string;
  instapay: string;
}

export interface Payment {
  id: number;
  user_id: number;
  track_id: number;
  amount: number | string;
  currency: string;
  status: PaymentStatus;
  payment_method: string;
  receipt_url: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentVerificationPayload {
  status: "VERIFIED" | "REJECTED";
  rejection_reason?: string | null;
}
