import type { Assignment } from "@/types/assignment";
import { api } from "./api";

export const assignmentService = {
  async getByTrack(
    trackId: number,
    limit = 100,
  ): Promise<Assignment[]> {
    const response = await api.get<Assignment[]>("/assignments", {
      params: {
        track_id: trackId,
        limit,
      },
    });

    return response.data;
  },
};
