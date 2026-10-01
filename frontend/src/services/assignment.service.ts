import type { Assignment, AssignmentCreate, AssignmentFilters, AssignmentUpdate } from "@/types/assignment";
import { api } from "./api";

const endpoint = "/api/v1/assignments";

export const assignmentService = {
  async list(filters: AssignmentFilters = {}, signal?: AbortSignal): Promise<Assignment[]> {
    return (await api.get<Assignment[]>(endpoint, { params: filters, signal })).data;
  },
  async get(id: number, signal?: AbortSignal): Promise<Assignment> {
    return (await api.get<Assignment>(`${endpoint}/${id}`, { signal })).data;
  },
  async create(data: AssignmentCreate): Promise<Assignment> {
    return (await api.post<Assignment>(endpoint, data)).data;
  },
  async update(id: number, data: AssignmentUpdate): Promise<Assignment> {
    return (await api.patch<Assignment>(`${endpoint}/${id}`, data)).data;
  },
  async remove(id: number): Promise<void> {
    await api.delete(`${endpoint}/${id}`);
  },
};
