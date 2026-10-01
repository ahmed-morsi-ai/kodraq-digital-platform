import { api } from "./api";
import type { GraduationEligibility, GraduationResult } from "@/types/graduation";

export const graduationService = {
  async getEligibility(trackId: number, userId?: number, signal?: AbortSignal): Promise<GraduationEligibility> {
    const response = await api.get<GraduationEligibility>("/api/v1/graduation/status", {
      params: { track_id: trackId, ...(userId === undefined ? {} : { user_id: userId }) }, signal,
    });
    return response.data;
  },

  async getResults(trackId: number, skip = 0, signal?: AbortSignal): Promise<GraduationResult[]> {
    const response = await api.get<GraduationResult[]>("/api/v1/graduation/results", {
      params: { track_id: trackId, skip, limit: 25 }, signal,
    });
    return response.data;
  },

  async getResult(resultId: number, signal?: AbortSignal): Promise<GraduationResult> {
    const response = await api.get<GraduationResult>(`/api/v1/graduation/results/${resultId}`, { signal });
    return response.data;
  },

  async finalize(trackId: number, userId: number): Promise<GraduationResult> {
    const response = await api.post<GraduationResult>(`/api/v1/graduation/finalize/${userId}`, {}, {
      params: { track_id: trackId },
    });
    return response.data;
  },
};
