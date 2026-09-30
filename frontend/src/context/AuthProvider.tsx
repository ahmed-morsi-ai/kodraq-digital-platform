import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { AuthService } from "@/services/auth.service";
import type { LoginCredentials, User } from "@/types/auth";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(() =>
    Boolean(localStorage.getItem("access_token")),
  );

  useEffect(() => {
    if (!localStorage.getItem("access_token")) return;
    let active = true;
    void AuthService.getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((error: unknown) => {
        console.error("Failed to fetch user context", error);
        localStorage.removeItem("access_token");
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener("auth-unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("auth-unauthorized", handleUnauthorized);
    };
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    const data = await AuthService.login(credentials);
    localStorage.setItem("access_token", data.access_token);
    try {
      const currentUser = await AuthService.getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      localStorage.removeItem("access_token");
      setUser(null);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}