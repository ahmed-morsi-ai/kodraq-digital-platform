import { api } from "./api";
import type { User, LoginCredentials, TokenResponse } from "../types/auth";

export const AuthService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    // OAuth2PasswordBearer expects form-data format for login
    const formData = new URLSearchParams();
    formData.append("username", credentials.username);
    formData.append("password", credentials.password);

    const response = await api.post<TokenResponse>("/api/v1/login/access-token", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/users/me");
    return response.data;
  },
};
