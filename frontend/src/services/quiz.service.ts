import { api } from "./api";
import type {
  QuizAttempt,
  QuizAttemptSubmit,
  QuizResult,
  StudentQuiz,
} from "@/types/quiz";

export const quizService = {
  async getAvailableQuizzes(params: {
    trackId?: number;
    lessonId?: number;
  }): Promise<StudentQuiz[]> {
    const response = await api.get<StudentQuiz[]>("/api/v1/quizzes", {
      params: {
        track_id: params.trackId,
        lesson_id: params.lessonId,
      },
    });

    return response.data;
  },

  async getQuiz(quizId: number): Promise<StudentQuiz> {
    const response = await api.get<StudentQuiz>(`/api/v1/quizzes/${quizId}`);
    return response.data;
  },

  async startAttempt(quizId: number): Promise<QuizAttempt> {
    const response = await api.post<QuizAttempt>(
      `/api/v1/quizzes/${quizId}/attempts`,
    );
    return response.data;
  },

  async getAttempt(attemptId: number): Promise<QuizAttempt> {
    const response = await api.get<QuizAttempt>(
      `/api/v1/quiz-attempts/${attemptId}`,
    );
    return response.data;
  },

  async submitAttempt(
    attemptId: number,
    payload: QuizAttemptSubmit,
  ): Promise<QuizAttempt> {
    const response = await api.post<QuizAttempt>(
      `/api/v1/quiz-attempts/${attemptId}/submit`,
      payload,
    );
    return response.data;
  },

  async getResult(attemptId: number): Promise<QuizResult> {
    const response = await api.get<QuizResult>(
      `/api/v1/quiz-attempts/${attemptId}/results`,
    );
    return response.data;
  },
};
