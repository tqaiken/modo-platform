import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import DashboardLayout from "./components/dashboard/DashboardLayout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DeveloperPage from "./pages/DeveloperPage";
import VerifierPage from "./pages/VerifierPage";
import CuratorPage from "./pages/CuratorPage";
import QuestionEditorPage from "./pages/QuestionEditorPage";
import QuestionViewPage from "./pages/QuestionViewPage";

function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode;
  allowedRoles?: string[];
}) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function DefaultRedirect() {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  const roleRedirects: Record<string, string> = {
    DEVELOPER: "/developer",
    VERIFIER: "/verifier",
    CURATOR: "/curator",
  };

  return <Navigate to={roleRedirects[user.role] || "/developer"} replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DefaultRedirect />} />

        {/* Developer */}
        <Route
          path="/developer"
          element={
            <ProtectedRoute allowedRoles={["DEVELOPER"]}>
              <DeveloperPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/questions/new"
          element={
            <ProtectedRoute allowedRoles={["DEVELOPER"]}>
              <QuestionEditorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/questions/:id/edit"
          element={
            <ProtectedRoute allowedRoles={["DEVELOPER"]}>
              <QuestionEditorPage />
            </ProtectedRoute>
          }
        />

        {/* Verifier */}
        <Route
          path="/verifier"
          element={
            <ProtectedRoute allowedRoles={["VERIFIER"]}>
              <VerifierPage />
            </ProtectedRoute>
          }
        />

        {/* Curator */}
        <Route
          path="/curator"
          element={
            <ProtectedRoute allowedRoles={["CURATOR"]}>
              <CuratorPage />
            </ProtectedRoute>
          }
        />

        {/* Shared */}
        <Route
          path="/questions/:id"
          element={
            <ProtectedRoute>
              <QuestionViewPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
