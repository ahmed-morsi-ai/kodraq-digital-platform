import { api } from "./api";
import type {
  Payment,
  PaymentInstructions,
  PaymentVerificationPayload,
} from "@/types/payment";

export const paymentService = {
  async getInstructions(): Promise<PaymentInstructions> {
    const response = await api.get<PaymentInstructions>("/payments/instructions");
    return response.data;
  },

  async submitPayment(
    trackId: number,
    method: string,
    receiptFile: File,
  ): Promise<Payment> {
    const formData = new FormData();
    formData.append("track_id", String(trackId));
    formData.append("payment_method", method);
    formData.append("receipt", receiptFile);

    const response = await api.post<Payment>("/payments/submit", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  },

  async getMyPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/payments/me");
    return response.data;
  },

  async getAdminPayments(): Promise<Payment[]> {
    const response = await api.get<Payment[]>("/payments", {
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
      `/payments/${paymentId}/verify`,
      payload,
    );
    return response.data;
  },
};
