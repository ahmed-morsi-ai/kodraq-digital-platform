import type {
  Lesson,
  LessonCreate,
  Resource,
  ResourceCreate,
  Track,
  TrackCreate,
  TrackCurriculum,
  TrackModule,
  TrackModuleCreate,
  TrackSummary,
} from "@/types/track";
import { api } from "./api";

export const trackService = {
  async getActiveTracks(): Promise<TrackSummary[]> {
    const response = await api.get<TrackSummary[]>("/tracks");
    return response.data;
  },

  async getCurriculum(trackId: number): Promise<TrackCurriculum> {
    const response = await api.get<TrackCurriculum>(
      `/tracks/${trackId}/curriculum`,
    );

    return response.data;
  },

  async createTrack(payload: TrackCreate): Promise<Track> {
    const response = await api.post<Track>("/tracks", payload);
    return response.data;
  },

  async createModule(
    trackId: number,
    payload: TrackModuleCreate,
  ): Promise<TrackModule> {
    const response = await api.post<TrackModule>(
      `/tracks/${trackId}/modules`,
      payload,
    );

    return response.data;
  },

  async createLesson(
    moduleId: number,
    payload: LessonCreate,
  ): Promise<Lesson> {
    const response = await api.post<Lesson>(
      `/tracks/modules/${moduleId}/lessons`,
      payload,
    );

    return response.data;
  },

  async createResource(
    moduleId: number,
    payload: ResourceCreate,
  ): Promise<Resource> {
    const response = await api.post<Resource>(
      `/tracks/modules/${moduleId}/resources`,
      payload,
    );

    return response.data;
  },
};
