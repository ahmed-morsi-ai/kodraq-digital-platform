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
    <div className="min-h-screen bg-[#f8fbff] text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-6 px-5 sm:px-8">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#5b9bd5] text-xs font-black text-white shadow-sm shadow-blue-100">
              KD
            </div>
            <div>
              <div className="text-sm font-black tracking-tight text-slate-900">
                Kodraq Digital
              </div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">
                Learn. Build. Automate.
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {navigation.map((item) => {
              const isActive =
                location.pathname === item.href ||
                (item.href !== "/dashboard" &&
                  location.pathname.startsWith(`${item.href}/`));

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`rounded-full px-4 py-2 text-xs font-semibold transition ${
                    isActive
                      ? "bg-blue-50 text-[#4a89c3]"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <Link
            to="/"
            className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:inline-flex"
          >
            Home
          </Link>
        </div>
      </header>

      <main className="min-h-[calc(100vh-64px)]">
        <Outlet />
      </main>
    </div>
  );
}