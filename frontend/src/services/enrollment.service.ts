import { api } from "./api";
import type {
  Enrollment,
  EnrollmentCreate,
  EnrollmentDetail,
  EnrollmentUpdate,
} from "@/types/enrollment";
import type {
  LessonProgress,
  ProgressCreatePayload,
  ProgressUpdatePayload,
} from "@/types/progress";

export const enrollmentService = {
  async enroll(payload: EnrollmentCreate): Promise<Enrollment> {
    const response = await api.post<Enrollment>("/api/v1/enrollments", payload);
    return response.data;
  },

  async getMyEnrollments(): Promise<Enrollment[]> {
    const response = await api.get<Enrollment[]>("/api/v1/enrollments/me");
    return response.data;
  },

  async getEnrollment(enrollmentId: number): Promise<EnrollmentDetail> {
    const response = await api.get<EnrollmentDetail>(
      `/api/v1/enrollments/${enrollmentId}`,
    );
    return response.data;
  },

  async getTrackEnrollments(trackId: number): Promise<Enrollment[]> {
    const response = await api.get<Enrollment[]>(
      `/api/v1/enrollments/track/${trackId}`,
    );
    return response.data;
  },

  async updateEnrollment(
    enrollmentId: number,
    payload: EnrollmentUpdate,
  ): Promise<Enrollment> {
    const response = await api.patch<Enrollment>(
      `/api/v1/enrollments/${enrollmentId}`,
      payload,
    );
    return response.data;
  },

  async getProgress(enrollmentId: number): Promise<LessonProgress[]> {
    const response = await api.get<LessonProgress[]>(
      `/api/v1/enrollments/${enrollmentId}/progress`,
    );
    return response.data;
  },

  async createProgress(
    enrollmentId: number,
    payload: ProgressCreatePayload,
  ): Promise<LessonProgress> {
    const response = await api.post<LessonProgress>(
      `/api/v1/enrollments/${enrollmentId}/progress`,
      payload,
    );
    return response.data;
  },

  async updateProgress(
    enrollmentId: number,
    progressId: number,
    payload: ProgressUpdatePayload,
  ): Promise<LessonProgress> {
    const response = await api.patch<LessonProgress>(
      `/api/v1/enrollments/${enrollmentId}/progress/${progressId}`,
      payload,
    );
    return response.data;
  },
};
