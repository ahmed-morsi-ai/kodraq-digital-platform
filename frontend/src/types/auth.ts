export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  role?: string | null;
  role_name: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegistrationPayload {
  email: string;
  full_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}