export type PaymentStatus =
  | "PENDING_VERIFICATION"
  | "VERIFIED"
  | "REJECTED";

export type PaymentMethod = "VODAFONE_CASH" | "INSTAPAY" | "BANK_TRANSFER";

export interface PaymentInstructions {
  vodafone_cash: string;
  instapay: string;
  bank_transfer: string;
}

export interface Payment {
  id: number;
  user_id: number;
  track_id: number;
  amount: number | string;
  currency: string;
  status: PaymentStatus;
  payment_method: string;
  transfer_reference?: string | null;
  receipt_url: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentVerificationPayload {
  status: "VERIFIED" | "REJECTED";
  rejection_reason?: string | null;
}
