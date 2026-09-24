import { api } from "./api";
import type {
  Certificate,
  CertificateVerification,
} from "@/types/certificate";

export const certificateService = {
  async graduate(trackId: number): Promise<Certificate> {
    const response = await api.post<Certificate>("/api/v1/graduation/graduate", {
      track_id: trackId,
    });

    return response.data;
  },

  async getMyCertificates(): Promise<Certificate[]> {
    const response = await api.get<Certificate[]>("/api/v1/certificates/me");
    return response.data;
  },

  async verifyCertificate(code: string): Promise<CertificateVerification> {
    const response = await api.get<CertificateVerification>(
      `/api/v1/certificates/verify/${encodeURIComponent(code)}`,
    );

    return response.data;
  },
};
