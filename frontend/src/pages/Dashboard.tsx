import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield, UserCheck, BookOpen, LogOut } from "lucide-react";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 w-full">
      {/* Top Banner / Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Welcome back, {user?.full_name || user?.email || "Student"}!
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Here is your Kodraq Digital Bootcamp overview and active track progress.
          </p>
        </div>
        <Button variant="outline" onClick={handleLogout} className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-gray-200">
          <LogOut className="w-4 h-4" />
          Sign out
        </Button>
      </div>

      {/* Grid Stats / Profile Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="border-gray-200 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">User Profile</CardTitle>
            <UserCheck className="w-4 h-4 text-blue-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-lg font-semibold text-slate-900 truncate">{user?.email}</div>
            <p className="text-xs text-gray-500">
              Role: {user?.is_superuser ? "Administrator / Superuser" : "Bootcamp Student"}
            </p>
          </CardContent>
          <CardFooter className="pt-0">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${user?.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
              {user?.is_active ? "Active Account" : "Inactive Account"}
            </span>
          </CardFooter>
        </Card>

        {/* Security / Access Level Card */}
        <Card className="border-gray-200 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Access Status</CardTitle>
            <Shield className="w-4 h-4 text-indigo-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-lg font-semibold text-slate-900">
              {user?.is_superuser ? "Full System Access" : "Standard Student Access"}
            </div>
            <p className="text-xs text-gray-500">Secured via OAuth2 Bearer Token (JWT)</p>
          </CardContent>
          <CardFooter className="pt-0 text-xs text-gray-400">
            Session authenticated successfully
          </CardFooter>
        </Card>

        {/* Tracks Card */}
        <Card className="border-gray-200 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Enrolled Tracks</CardTitle>
            <BookOpen className="w-4 h-4 text-emerald-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-lg font-semibold text-slate-900">Backend & AI Engineering</div>
            <p className="text-xs text-gray-500">Python, FastAPI, Django & RAG Modules</p>
          </CardContent>
          <CardFooter className="pt-0 text-xs text-emerald-600 font-medium">
            Active enrollment
          </CardFooter>
        </Card>
      </div>

      {/* Main Content Area */}
      <Card className="border-gray-200 shadow-sm">
        <CardHeader>
          <CardTitle>Platform Quick Actions</CardTitle>
          <CardDescription>Select an operational module to proceed with your training or administration.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg border border-gray-100 bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer space-y-2">
            <h4 className="font-medium text-slate-900">Curriculum & Lessons</h4>
            <p className="text-xs text-gray-500">Explore technical track modules and assignments.</p>
          </div>
          <div className="p-4 rounded-lg border border-gray-100 bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer space-y-2">
            <h4 className="font-medium text-slate-900">AI Tutor RAG Hub</h4>
            <p className="text-xs text-gray-500">Interact with your dedicated track-specific AI assistant.</p>
          </div>
          <div className="p-4 rounded-lg border border-gray-100 bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer space-y-2">
            <h4 className="font-medium text-slate-900">Project Submissions</h4>
            <p className="text-xs text-gray-500">Upload and track your graduation capstone requirements.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
