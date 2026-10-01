import { api } from "./api";
import type { QuizAttempt, QuizAttemptSubmit, QuizResult, StudentQuiz } from "@/types/quiz";

export const quizService = {
  async getAvailableQuizzes(params: { trackId?: number; moduleId?: number; lessonId?: number; skip?: number }, signal?: AbortSignal): Promise<StudentQuiz[]> {
    const { data } = await api.get<StudentQuiz[]>("/api/v1/quizzes", {
      params: { track_id: params.trackId, module_id: params.moduleId, lesson_id: params.lessonId, skip: params.skip ?? 0, limit: 100 }, signal,
    });
    return data;
  },
  async getQuiz(quizId: number, signal?: AbortSignal): Promise<StudentQuiz> {
    return (await api.get<StudentQuiz>(`/api/v1/quizzes/${quizId}`, { signal })).data;
  },
  async startAttempt(quizId: number): Promise<QuizAttempt> {
    return (await api.post<QuizAttempt>(`/api/v1/quizzes/${quizId}/attempts`)).data;
  },
  async listAttempts(quizId: number, signal?: AbortSignal, skip = 0, limit = 100): Promise<QuizAttempt[]> {
    return (await api.get<QuizAttempt[]>(`/api/v1/quizzes/${quizId}/attempts`, { params: { skip, limit }, signal })).data;
  },
  async getAttempt(attemptId: number, signal?: AbortSignal): Promise<QuizAttempt> {
    return (await api.get<QuizAttempt>(`/api/v1/quiz-attempts/${attemptId}`, { signal })).data;
  },
  async submitAttempt(attemptId: number, payload: QuizAttemptSubmit): Promise<QuizAttempt> {
    return (await api.post<QuizAttempt>(`/api/v1/quiz-attempts/${attemptId}/submit`, payload)).data;
  },
  async getResult(attemptId: number, signal?: AbortSignal): Promise<QuizResult> {
    return (await api.get<QuizResult>(`/api/v1/quiz-attempts/${attemptId}/results`, { signal })).data;
  },
  async submitAndConfirm(attemptId: number, payload: QuizAttemptSubmit): Promise<QuizAttempt> {
    // Expiry finalizes on the server with an HTTP 400. A lost response can also
    // follow a successful commit; navigate only after verifying completion.
    try {
      return await quizService.submitAttempt(attemptId, payload);
    } catch (error) {
      try {
        const attempt = await quizService.getAttempt(attemptId);
        if (attempt.status === "COMPLETED") return attempt;
      } catch { /* Preserve the original submission error for retry. */ }
      throw error;
    }
  },
};
