import { api } from "./api";
import type {
  LoginCredentials,
  RegistrationPayload,
  TokenResponse,
  User,
} from "@/types/auth";

export const AuthService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    try {
      const formData = new URLSearchParams();
      formData.set("grant_type", "password");
      formData.set("username", credentials.username.trim());
      formData.set("password", credentials.password);

      const response = await api.post<TokenResponse>(
        "/api/v1/login/access-token",
        formData,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      return response.data;
    } catch (error: unknown) {
      const details = error as { response?: { data?: unknown }; message?: string };
      console.error(
        "AUTH ERROR DETAILS:",
        details.response?.data || details.message || error
      );
      throw error;
    }
  },

  async register(payload: RegistrationPayload): Promise<User> {
    try {
      const response = await api.post<User>("/api/v1/users", {
        email: payload.email.trim(),
        full_name: payload.full_name.trim(),
        password: payload.password,
      });

      return response.data;
    } catch (error: unknown) {
      const details = error as { response?: { data?: unknown }; message?: string };
      console.error(
        "AUTH ERROR DETAILS:",
        details.response?.data || details.message || error
      );
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/users/me");
    return response.data;
  },
};