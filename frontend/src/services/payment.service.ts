import { api } from "./api";
import type {
  Payment,
  PaymentCreatePayload,
  PaymentInstructions,
  PaymentMethod,
  PaymentVerificationPayload,
} from "@/types/payment";

export const paymentService = {
  async getInstructions(): Promise<PaymentInstructions> {
    const response = await api.get<PaymentInstructions>("/api/v1/payments/instructions");
    return response.data;
  },

  async submitPayment(
    trackId: number,
    method: PaymentMethod,
    receiptFile: File | null,
    transferReference: string,
    couponCode?: string,
  ): Promise<Payment> {
    const formData = new FormData();
    const payload: PaymentCreatePayload = {
      track_id: trackId,
      payment_method: method,
      transfer_reference: transferReference.trim(),
      ...(couponCode ? { coupon_code: couponCode } : {}),
    };
    formData.append("track_id", String(payload.track_id));
    formData.append("payment_method", payload.payment_method);
    formData.append("transfer_reference", payload.transfer_reference);
    if (payload.coupon_code) {
      formData.append("coupon_code", payload.coupon_code);
    }
    if (receiptFile) {
      formData.append("file", receiptFile);
    }

    const response = await api.post<Payment>("/api/v1/payments", formData);

    return response.data;
  },

  async getMyPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/api/v1/payments/me");
    return response.data;
  },

  async getAdminPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/api/v1/payments", {
      params: { status: "PENDING_VERIFICATION" },
    });
    return response.data;
  },

  async verifyPayment(
    paymentId: number,
    status: "VERIFIED" | "REJECTED",
    rejectionReason?: string,
  ): Promise<Payment> {
    const payload: PaymentVerificationPayload = {
      status,
      rejection_reason:
        status === "REJECTED" ? rejectionReason?.trim() || null : null,
    };

    const response = await api.patch<Payment>(
      `/api/v1/payments/${paymentId}/verify`,
      payload,
    );
    return response.data;
  },
};
