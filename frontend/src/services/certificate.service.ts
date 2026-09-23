import { api } from "./api";
import type {
  Certificate,
  CertificateVerification,
} from "@/types/certificate";

export const certificateService = {
  async graduate(trackId: number): Promise<Certificate> {
    const response = await api.post<Certificate>("/graduation/graduate", {
      track_id: trackId,
    });

    return response.data;
  },

  async getMyCertificates(): Promise<Certificate[]> {
    const response = await api.get<Certificate[]>("/certificates/me");
    return response.data;
  },

  async verifyCertificate(code: string): Promise<CertificateVerification> {
    const response = await api.get<CertificateVerification>(
      `/certificates/verify/${encodeURIComponent(code)}`,
    );

    return response.data;
  },
};
