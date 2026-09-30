import { LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

interface RoleDashboardProps {
  role: "client" | "instructor";
}

export default function RoleDashboard({ role }: RoleDashboardProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const title = role === "client" ? "Client dashboard" : "Instructor dashboard";

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#f8fbff] text-slate-900">
      <header className="flex min-h-16 items-center justify-between border-b border-slate-200 bg-white px-5 sm:px-8">
        <Link to="/" className="text-sm font-black text-slate-900">
          Kodraq Digital
        </Link>
        <Button variant="outline" onClick={handleLogout}>
          <LogOut aria-hidden="true" className="mr-2 size-4" />
          Sign out
        </Button>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16">
        <p className="text-xs font-bold uppercase text-sky-700">Workspace</p>
        <h1 className="mt-3 text-3xl font-black text-slate-950">{title}</h1>
        <p className="mt-3 text-base text-slate-600">
          Welcome, {user?.full_name || "there"}.
        </p>
      </main>
    </div>
  );
}