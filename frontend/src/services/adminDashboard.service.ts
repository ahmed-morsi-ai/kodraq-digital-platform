import { api } from "@/services/api";
import type {
  AdminLessonPayload,
  AdminLogs,
  AdminModulePayload,
  AdminStats,
  AdminStudent,
  AdminTrack,
  AdminTrackPayload,
} from "@/types/adminDashboard";
import type { Lesson, TrackModule } from "@/types/track";

export const adminDashboardService = {
  async getStats(): Promise<AdminStats> {
    const response = await api.get<AdminStats>("/api/admin/stats");
    return response.data;
  },

  async getStudents(search = ""): Promise<AdminStudent[]> {
    const response = await api.get<AdminStudent[]>("/api/admin/users", {
      params: search ? { search } : undefined,
    });
    return response.data;
  },

  async updateStudent(
    userId: number,
    update: { is_active: boolean },
  ): Promise<AdminStudent> {
    const response = await api.patch<AdminStudent>(`/api/admin/users/${userId}`, update);
    return response.data;
  },

  async activateSubscription(userId: number): Promise<{
    user_id: number;
    is_active: boolean;
    subscription_active: boolean;
    activated_enrollments: number;
  }> {
    const response = await api.post(
      `/api/admin/users/${userId}/activate-subscription`,
    );
    return response.data;
  },

  async getLogs(): Promise<AdminLogs> {
    const response = await api.get<AdminLogs>("/api/admin/logs");
    return response.data;
  },

  async getTracks(): Promise<AdminTrack[]> {
    const response = await api.get<AdminTrack[]>("/api/admin/content/tracks");
    return response.data;
  },

  async createTrack(payload: AdminTrackPayload): Promise<AdminTrack> {
    const response = await api.post<AdminTrack>("/api/admin/content/tracks", payload);
    return response.data;
  },

  async updateTrack(trackId: number, payload: Partial<AdminTrackPayload>): Promise<AdminTrack> {
    const response = await api.patch<AdminTrack>(`/api/admin/content/tracks/${trackId}`, payload);
    return response.data;
  },

  async deleteTrack(trackId: number): Promise<void> {
    await api.delete(`/api/admin/content/tracks/${trackId}`);
  },

  async createModule(trackId: number, payload: AdminModulePayload): Promise<TrackModule> {
    const response = await api.post<TrackModule>(
      `/api/admin/content/tracks/${trackId}/modules`,
      payload,
    );
    return response.data;
  },

  async updateModule(moduleId: number, payload: Partial<AdminModulePayload>): Promise<TrackModule> {
    const response = await api.patch<TrackModule>(`/api/admin/content/modules/${moduleId}`, payload);
    return response.data;
  },

  async deleteModule(moduleId: number): Promise<void> {
    await api.delete(`/api/admin/content/modules/${moduleId}`);
  },

  async createLesson(moduleId: number, payload: AdminLessonPayload): Promise<Lesson> {
    const response = await api.post<Lesson>(
      `/api/admin/content/modules/${moduleId}/lessons`,
      payload,
    );
    return response.data;
  },

  async updateLesson(lessonId: number, payload: Partial<AdminLessonPayload>): Promise<Lesson> {
    const response = await api.patch<Lesson>(`/api/admin/content/lessons/${lessonId}`, payload);
    return response.data;
  },

  async deleteLesson(lessonId: number): Promise<void> {
    await api.delete(`/api/admin/content/lessons/${lessonId}`);
  },
};