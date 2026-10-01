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
  async getByTrack(trackId: number, signal?: AbortSignal): Promise<TrainingProject> {
    const { data } = await api.get<TrainingProject>(
      `/api/v1/tracks/${trackId}/final-project`, { signal },
    );
    return data;
  },

  async getMySubmissions(
    params: { project_id?: number; skip?: number; limit?: number } = {},
    signal?: AbortSignal,
  ): Promise<ProjectSubmission[]> {
    const { data } = await api.get<ProjectSubmission[]>(
      "/api/v1/final-projects/submissions/me", { params, signal },
    );
    return data;
  },

  async getByProject(projectId: number, skip = 0, signal?: AbortSignal): Promise<ProjectSubmission[]> {
    const { data } = await api.get<ProjectSubmission[]>(
      `/api/v1/final-projects/${projectId}/submissions`,
      { params: { skip, limit: 50 }, signal },
    );
    return data;
  },

  async getSubmission(submissionId: number, signal?: AbortSignal): Promise<ProjectSubmission> {
    const { data } = await api.get<ProjectSubmission>(
      `/api/v1/final-projects/submissions/${submissionId}`, { signal },
    );
    return data;
  },

  async createSubmission(projectId: number, payload: ProjectSubmissionCreate): Promise<ProjectSubmission> {
    const { data } = await api.post<ProjectSubmission>(
      `/api/v1/final-projects/${projectId}/submissions`, payload,
    );
    return data;
  },

  async updateSubmission(submissionId: number, payload: ProjectSubmissionUpdate): Promise<ProjectSubmission> {
    const { data } = await api.patch<ProjectSubmission>(
      `/api/v1/final-projects/submissions/${submissionId}`, payload,
    );
    return data;
  },

  async createReview(submissionId: number, payload: ProjectReviewCreate): Promise<ProjectReview> {
    const { data } = await api.post<ProjectReview>(
      `/api/v1/final-projects/submissions/${submissionId}/reviews`, payload,
    );
    return data;
  },
};

/** Preserve a created draft if submission fails; reconcile uncertain writes before retry. */
export async function saveProjectSubmission(
  projectId: number,
  submission: ProjectSubmission | null,
  payload: ProjectSubmissionCreate,
  submit: boolean,
  onSaved: (submission: ProjectSubmission) => void,
): Promise<void> {
  let current = submission;
  try {
    if (!current) {
      current = await finalProjectService.createSubmission(projectId, payload);
      onSaved(current);
      if (!submit) return;
    }
    current = await finalProjectService.updateSubmission(current.id, {
      ...payload,
      ...(submit ? { status: "SUBMITTED" as const } : {}),
    });
    onSaved(current);
  } catch (error) {
    try {
      const saved = current
        ? await finalProjectService.getSubmission(current.id)
        : (await finalProjectService.getMySubmissions({ project_id: projectId, limit: 1 }))[0];
      if (saved) onSaved(saved);
    } catch {
      // Keep the original failure and entered values when reconciliation is unavailable.
    }
    throw error;
  }
}

/** A committed review stays successful even if refreshing the full history fails. */
export async function reviewProjectSubmission(
  submission: ProjectSubmission,
  payload: ProjectReviewCreate,
): Promise<ProjectSubmission> {
  const review = await finalProjectService.createReview(submission.id, payload);
  try {
    return await finalProjectService.getSubmission(submission.id);
  } catch {
    return {
      ...submission,
      status: review.status_decision,
      updated_at: review.updated_at,
      reviews: [...submission.reviews, review],
    };
  }
}
