import type {
  Enrollment,
  EnrollmentCreate,
  EnrollmentDetail,
  EnrollmentUpdate,
  StudentProgress,
  StudentProgressCreate,
  StudentProgressDetail,
  StudentProgressUpdate,
} from "@/types/enrollment";
import { api } from "./api";

export const enrollmentService = {
  async enroll(payload: EnrollmentCreate): Promise<Enrollment> {
    const response = await api.post<Enrollment>("/enrollments", payload);
    return response.data;
  },

  async getMyEnrollments(): Promise<Enrollment[]> {
    const response = await api.get<Enrollment[]>("/enrollments/me");
    return response.data;
  },

  async getEnrollment(enrollmentId: number): Promise<EnrollmentDetail> {
    const response = await api.get<EnrollmentDetail>(
      `/enrollments/${enrollmentId}`,
    );

    return response.data;
  },

  async getTrackEnrollments(trackId: number): Promise<Enrollment[]> {
    const response = await api.get<Enrollment[]>(
      `/enrollments/track/${trackId}`,
    );

    return response.data;
  },

  async updateEnrollment(
    enrollmentId: number,
    payload: EnrollmentUpdate,
  ): Promise<Enrollment> {
    const response = await api.patch<Enrollment>(
      `/enrollments/${enrollmentId}`,
      payload,
    );

    return response.data;
  },

  async getProgress(
    enrollmentId: number,
  ): Promise<StudentProgressDetail[]> {
    const response = await api.get<StudentProgressDetail[]>(
      `/enrollments/${enrollmentId}/progress`,
    );

    return response.data;
  },

  async createProgress(
    enrollmentId: number,
    payload: StudentProgressCreate,
  ): Promise<StudentProgress> {
    const response = await api.post<StudentProgress>(
      `/enrollments/${enrollmentId}/progress`,
      payload,
    );

    return response.data;
  },

  async updateProgress(
    enrollmentId: number,
    progressId: number,
    payload: StudentProgressUpdate,
  ): Promise<StudentProgress> {
    const response = await api.patch<StudentProgress>(
      `/enrollments/${enrollmentId}/progress/${progressId}`,
      payload,
    );

    return response.data;
  },
};
