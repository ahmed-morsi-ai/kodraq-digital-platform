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
  vodafone_cash: "01000000000",
  instapay: "ahmed_morsi2672@instapay",
  bank_transfer: "CIB - EG...................",
  vodafone_cash_instructions: "قم بالتحويل إلى رقم فودافون كاش أعلاه، ثم أدخل رقم الموبايل المحول منه وأرفق صورة الإيصال.",
  instapay_instructions: "قم بالتحويل عبر تطبيق انستاباي إلى العنوان أعلاه، ثم أدخل رقم الهواتف/مرجع التحويل وأرفق صورة الإيصال.",
  bank_transfer_instructions: "قم بالتحويل البنكي لحساب الشركة، ثم أرفق إيصال التحويل.",
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

export interface PaymentVerificationPayload {
  status: "VERIFIED" | "REJECTED";
  rejection_reason?: string | null;
}
