import type {
  ProjectReview,
  ProjectReviewCreate,
  ProjectSubmission,
  ProjectSubmissionCreate,
  ProjectSubmissionUpdate,
  TrainingProject,
} from "@/types/finalProject";
import { api } from "./api";

export const finalProjectService = {
  async getByTrack(trackId: number): Promise<TrainingProject> {
    const response = await api.get<TrainingProject>(
      `/tracks/${trackId}/final-project`,
    );

    return response.data;
  },

  async getMySubmissions(): Promise<ProjectSubmission[]> {
    const response = await api.get<ProjectSubmission[]>(
      "/final-projects/submissions/me",
    );

    return response.data;
  },

  async getByProject(projectId: number): Promise<ProjectSubmission[]> {
    const response = await api.get<ProjectSubmission[]>(
      `/final-projects/${projectId}/submissions`,
    );

    return response.data;
  },

  async createSubmission(
    projectId: number,
    payload: ProjectSubmissionCreate,
  ): Promise<ProjectSubmission> {
    const response = await api.post<ProjectSubmission>(
      `/final-projects/${projectId}/submissions`,
      payload,
    );

    return response.data;
  },

  async updateSubmission(
    submissionId: number,
    payload: ProjectSubmissionUpdate,
  ): Promise<ProjectSubmission> {
    const response = await api.patch<ProjectSubmission>(
      `/final-projects/submissions/${submissionId}`,
      payload,
    );

    return response.data;
  },

  async getReviews(submissionId: number): Promise<ProjectReview[]> {
    const response = await api.get<ProjectReview[]>(
      `/final-projects/submissions/${submissionId}/reviews`,
    );

    return response.data;
  },

  async createReview(
    submissionId: number,
    payload: ProjectReviewCreate,
  ): Promise<ProjectReview> {
    const response = await api.post<ProjectReview>(
      `/final-projects/submissions/${submissionId}/reviews`,
      payload,
    );

    return response.data;
  },
};
