import { BrowserRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import RootLayout from "./layouts/RootLayout";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import MyLearning from "./pages/MyLearning";
import MyCertificates from "./pages/MyCertificates";
import NotFound from "./pages/NotFound";
import QuizResults from "./pages/QuizResults";
import QuizTaker from "./pages/QuizTaker";
import FinalProject from "./pages/FinalProject";
import TrackDetail from "./pages/TrackDetail";
import Tracks from "./pages/Tracks";
import AdminPayments from "./pages/AdminPayments";
import VerifyCertificate from "./pages/VerifyCertificate";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/verify/:code" element={<VerifyCertificate />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<RootLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
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
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
