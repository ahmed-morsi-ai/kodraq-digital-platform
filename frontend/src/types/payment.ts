export type PaymentStatus =
  | "PENDING_VERIFICATION"
  | "VERIFIED"
  | "REJECTED";

export type PaymentMethod = "VODAFONE_CASH" | "INSTAPAY" | "BANK_TRANSFER";

export interface PaymentInstructions {
  vodafone_cash: string;
  instapay: string;
  bank_transfer: string;
  vodafone_cash_instructions: string;
  instapay_instructions: string;
  bank_transfer_instructions: string;
}

export const DEFAULT_PAYMENT_INSTRUCTIONS: PaymentInstructions = {
  vodafone_cash: "01140225360",
  instapay: "ahmed_morsi2672@instapay",
  bank_transfer: "01140225360",
  vodafone_cash_instructions: "قم بالتحويل إلى محفظة فودافون كاش رقم 01140225360، ثم أدخل رقم الموبايل المحول منه وأرفق صورة الإيصال.",
  instapay_instructions: "تُستقبل التحويلات عبر انستاباي على العنوان ahmed_morsi2672@instapay أو مباشرةً إلى محفظة فودافون كاش رقم 01140225360.",
  bank_transfer_instructions: "يرجى التحويل مباشرةً إلى محفظة فودافون كاش رقم 01140225360.",
};

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

export interface PaymentCreatePayload {
  track_id: number;
  payment_method: PaymentMethod;
  transfer_reference: string;
  coupon_code?: string;
}

export interface PaymentVerificationPayload {
  status: "VERIFIED" | "REJECTED";
  rejection_reason?: string | null;
}
