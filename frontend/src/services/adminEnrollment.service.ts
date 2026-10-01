import { api } from "@/services/api";
import type { AdminEnrollment } from "@/types/enrollment";

export const adminEnrollmentService = {
  async getAll(): Promise<AdminEnrollment[]> {
    const response = await api.get<AdminEnrollment[]>("/api/v1/admin/enrollments");
    return response.data;
  },

  async updateStatus(
    enrollmentId: number,
    status: "active" | "cancelled",
  ): Promise<AdminEnrollment> {
    const response = await api.patch<AdminEnrollment>(
      `/api/v1/admin/enrollments/${enrollmentId}/status`,
      { status },
    );
    return response.data;
  },
};