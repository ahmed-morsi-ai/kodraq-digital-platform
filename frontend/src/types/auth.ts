export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface LoginCredentials {
  username: string; // The backend OAuth2 expects 'username' (which we map to email)
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
