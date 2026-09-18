import { Outlet } from "react-router-dom";

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col text-slate-900">
      <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm flex items-center justify-between">
        <h1 className="text-xl font-bold text-blue-600">Kodraq Platform</h1>
        <div className="text-sm text-gray-500">Admin App Shell</div>
      </header>
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
