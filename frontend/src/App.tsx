import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./contexts/AuthContext";
import DashboardLayout from "./components/dashboard/DashboardLayout";

import LoginPage from "./pages/LoginPage";
import SuperAdminPage from "./pages/SuperAdminPage";
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

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (
    allowedRoles &&
    !allowedRoles.includes(user.role)
  ) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}


function DefaultRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const roleRedirects: Record<string, string> = {
    SUPER_ADMIN: "/admin",
    DEVELOPER: "/developer",
    VERIFIER: "/verifier",
    CURATOR: "/curator",
  };

  return (
    <Navigate
      to={roleRedirects[user.role] || "/login"}
      replace
    />
  );
}


export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={<LoginPage />}
      />

      {/* Protected layout */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={<DefaultRedirect />}
        />

        {/* Super Admin */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute
              allowedRoles={["SUPER_ADMIN"]}
            >
              <SuperAdminPage />
            </ProtectedRoute>
          }
        />

        {/* Developer */}
        <Route
          path="/developer"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <DeveloperPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/questions/new"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <QuestionEditorPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/questions/:id/edit"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <QuestionEditorPage />
            </ProtectedRoute>
          }
        />

        {/* Verifier */}
        <Route
          path="/verifier"
          element={
            <ProtectedRoute
              allowedRoles={["VERIFIER"]}
            >
              <VerifierPage />
            </ProtectedRoute>
          }
        />

        {/* Curator */}
        <Route
          path="/curator"
          element={
            <ProtectedRoute
              allowedRoles={["CURATOR"]}
            >
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

      {/* Public registration is disabled */}
      <Route
        path="/register"
        element={<Navigate to="/login" replace />}
      />

      {/* Catch-all */}
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
}