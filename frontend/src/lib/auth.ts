import type { User } from "@/types/auth";

export function getUserRole(user: User): string {
  if (user.is_superuser) return "admin";
  return (user.role_name ?? user.role ?? "student").trim().toLowerCase();
}

export function getDashboardPath(user: User): string {
  switch (getUserRole(user)) {
    case "student":
      return "/dashboard";
    case "client":
      return "/client-dashboard";
    case "instructor":
      return "/instructor-dashboard";
    case "admin":
      return "/admin";
    default:
      return "/";
  }
}