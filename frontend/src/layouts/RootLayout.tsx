import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function RootLayout() {
  const location = useLocation();
  const { user } = useAuth();

  const navigation = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Tracks", href: "/tracks" },
    { label: "My Learning", href: "/my-learning" },
    { label: "Certificates", href: "/certificates" },
    ...(user?.is_superuser || user?.role === "admin"
      ? [{ label: "Payments", href: "/admin/payments" }]
      : []),
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-6 px-5 sm:px-8">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/10 text-xs font-black text-emerald-300">
              KD
            </div>
            <div>
              <div className="text-sm font-black">Kodraq Digital</div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-white/30">
                Platform
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-2 md:flex">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`rounded-full px-4 py-2 text-xs font-semibold transition ${
                    isActive
                      ? "bg-white/[0.08] text-white"
                      : "text-white/45 hover:bg-white/[0.05] hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="min-h-[calc(100vh-64px)]">
        <Outlet />
      </main>
    </div>
  );
}
