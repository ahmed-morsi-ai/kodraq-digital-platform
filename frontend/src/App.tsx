import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import RootLayout from "./layouts/RootLayout";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const MyLearning = lazy(() => import("./pages/MyLearning"));
const MyCertificates = lazy(() => import("./pages/MyCertificates"));
const NotFound = lazy(() => import("./pages/NotFound"));
const QuizResults = lazy(() => import("./pages/QuizResults"));
const QuizTaker = lazy(() => import("./pages/QuizTaker"));
const FinalProject = lazy(() => import("./pages/FinalProject"));
const TrackDetail = lazy(() => import("./pages/TrackDetail"));
const Tracks = lazy(() => import("./pages/Tracks"));
const AdminPayments = lazy(() => import("./pages/AdminPayments"));
const VerifyCertificate = lazy(() => import("./pages/VerifyCertificate"));
import RoleDashboard from "./pages/RoleDashboard";

function App() {
  return (
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center bg-[#f8fbff] text-sm text-slate-600">
            Loading workspace...
          </div>
        }
      >
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify/:code" element={<VerifyCertificate />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<RootLayout />}>
            <Route element={<ProtectedRoute allowedRoles={["student"]} />}>
              <Route path="/dashboard" element={<Dashboard />} />
            </Route>
            <Route path="/tracks" element={<Tracks />} />
            <Route path="/tracks/:trackId" element={<TrackDetail />} />
            <Route
              path="/tracks/:trackId/final-project"
              element={<FinalProject />}
            />
            <Route path="/my-learning" element={<MyLearning />} />
            <Route path="/admin/payments" element={<AdminPayments />} />
            <Route path="/certificates" element={<MyCertificates />} />
            <Route
              path="/quizzes/:quizId/attempts/:attemptId"
              element={<QuizTaker />}
            />
            <Route
              path="/quiz-attempts/:attemptId/results"
              element={<QuizResults />}
            />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={["client"]} />}>
            <Route
              path="/client-dashboard"
              element={<RoleDashboard role="client" />}
            />
          </Route>
          <Route
            element={
              <ProtectedRoute allowedRoles={["instructor", "admin"]} />
            }
          >
            <Route
              path="/instructor-dashboard"
              element={<RoleDashboard role="instructor" />}
            />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
