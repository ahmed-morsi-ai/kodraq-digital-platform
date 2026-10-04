import type {
  Lesson,
  LessonCreate,
  LessonQuizPrompt,
  LessonQuizResult,
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

function isLessonQuizPrompt(value: unknown): value is LessonQuizPrompt {
  if (!value || typeof value !== "object") return false;
  const question = value as Partial<LessonQuizPrompt>;
  return typeof question.id === "number"
    && typeof question.question === "string"
    && Array.isArray(question.options)
    && question.options.length > 0
    && question.options.every((option) => typeof option === "string");
}

export function parseLessonQuiz(rawQuiz: Lesson["quiz_data"]): LessonQuizPrompt[] {
  let parsedQuiz: unknown = rawQuiz;
  if (typeof rawQuiz === "string") {
    try {
      parsedQuiz = JSON.parse(rawQuiz);
    } catch (parseError) {
      console.error("Unable to parse lesson quiz data", parseError);
      return [];
    }
  }
  return Array.isArray(parsedQuiz)
    ? parsedQuiz.filter(isLessonQuizPrompt).map(({ id, question, options }) => ({
      id, question, options,
    }))
    : [];
}

export const trackService = {
  async getActiveTracks(): Promise<TrackSummary[]> {
    const response = await api.get<TrackSummary[]>("/api/v1/tracks");
    return response.data;
  },

  async getCurriculum(trackId: number): Promise<TrackCurriculum> {
    const response = await api.get<TrackCurriculum>(
      `/api/v1/tracks/${trackId}/curriculum`,
    );

    return response.data;
  },

  async submitLessonQuiz(
    trackId: number,
    lessonId: number,
    answers: { question_id: number; selected_index: number }[],
  ): Promise<LessonQuizResult> {
    const response = await api.post<LessonQuizResult>(
      `/api/v1/tracks/${trackId}/lessons/${lessonId}/quiz/submit`,
      { answers },
    );
    return response.data;
  },

  async createTrack(payload: TrackCreate): Promise<Track> {
    const response = await api.post<Track>("/api/v1/tracks", payload);
    return response.data;
  },

  async createModule(
    trackId: number,
    payload: TrackModuleCreate,
  ): Promise<TrackModule> {
    const response = await api.post<TrackModule>(
      `/api/v1/tracks/${trackId}/modules`,
      payload,
    );

    return response.data;
  },

  async createLesson(
    moduleId: number,
    payload: LessonCreate,
  ): Promise<Lesson> {
    const response = await api.post<Lesson>(
      `/api/v1/tracks/modules/${moduleId}/lessons`,
      payload,
    );

    return response.data;
  },

  async createResource(
    moduleId: number,
    payload: ResourceCreate,
  ): Promise<Resource> {
    const response = await api.post<Resource>(
      `/api/v1/tracks/modules/${moduleId}/resources`,
      payload,
    );

    return response.data;
  },
};
