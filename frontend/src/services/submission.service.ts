import { api } from "./api";
import type { ReviewInput, Submission, SubmissionDetail, SubmissionFile, SubmissionInput } from "@/types/submission";

const endpoint = "/api/v1/submissions";

export const submissionService = {
  async listMine(assignmentId: number, skip = 0, signal?: AbortSignal): Promise<Submission[]> {
    return (await api.get<Submission[]>(`${endpoint}/me`, { params: { assignment_id: assignmentId, skip, limit: 100 }, signal })).data;
  },
  async listForAssignment(assignmentId: number, skip = 0, signal?: AbortSignal): Promise<Submission[]> {
    return (await api.get<Submission[]>(`/api/v1/assignments/${assignmentId}/submissions`, { params: { skip, limit: 100 }, signal })).data;
  },
  async get(id: number, signal?: AbortSignal): Promise<SubmissionDetail> {
    return (await api.get<SubmissionDetail>(`${endpoint}/${id}`, { signal })).data;
  },
  async create(assignmentId: number, data: SubmissionInput): Promise<Submission> {
    return (await api.post<Submission>(endpoint, { assignment_id: assignmentId, ...data })).data;
  },
  async update(id: number, data: SubmissionInput & { status?: "SUBMITTED" }): Promise<Submission> {
    return (await api.patch<Submission>(`${endpoint}/${id}`, data)).data;
  },
  async review(id: number, data: ReviewInput): Promise<Submission> {
    return (await api.post<Submission>(`${endpoint}/${id}/review`, data)).data;
  },
  async upload(id: number, files: File[]): Promise<SubmissionFile[]> {
    const data = new FormData();
    files.forEach((file) => data.append("files", file));
    return (await api.post<SubmissionFile[]>(`${endpoint}/${id}/files`, data, { headers: { "Content-Type": undefined } })).data;
  },
  async removeFile(id: number, fileId: string): Promise<void> {
    await api.delete(`${endpoint}/${id}/files/${fileId}`);
  },
  async download(id: number, fileId: string): Promise<Blob> {
    return (await api.get<Blob>(`${endpoint}/${id}/files/${fileId}/download`, { responseType: "blob" })).data;
  },
};
