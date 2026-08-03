import type { ReactNode } from "react";
import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import DashboardLayout from "./components/dashboard/DashboardLayout";
import { useAuth } from "./contexts/AuthContext";

import CuratorPage from "./pages/CuratorPage";
import DeveloperPage from "./pages/DeveloperPage";
import LearningObjectivesPage from "./pages/LearningObjectivesPage";
import LoginPage from "./pages/LoginPage";
import QuestionEditorPage from "./pages/QuestionEditorPage";
import QuestionViewPage from "./pages/QuestionViewPage";
import SuperAdminPage from "./pages/SuperAdminPage";
import VariantCreatePage from "./pages/VariantCreatePage";
import VariantDetailPage from "./pages/VariantDetailPage";
import VerifierPage from "./pages/VerifierPage";


type ProtectedRouteProps = {
  children: ReactNode;
  allowedRoles?: string[];
};


function LoadingScreen() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
    </div>
  );
}


function ProtectedRoute({
  children,
  allowedRoles,
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (user === null) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  if (
    allowedRoles !== undefined &&
    !allowedRoles.includes(user.role)
  ) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return <>{children}</>;
}


function DefaultRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (user === null) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  const roleRedirects: Record<string, string> = {
    SUPER_ADMIN: "/admin",
    DEVELOPER: "/developer",
    VERIFIER: "/verifier",
    CURATOR: "/curator",
  };

  const destination =
    roleRedirects[user.role] ?? "/login";

  return (
    <Navigate
      to={destination}
      replace
    />
  );
}


export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={<LoginPage />}
      />

      <Route
        path="/register"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />

      {/* Protected application */}
      <Route
        path="/"
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
          path="admin"
          element={
            <ProtectedRoute
              allowedRoles={["SUPER_ADMIN"]}
            >
              <SuperAdminPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="admin/learning-objectives"
          element={
            <ProtectedRoute
              allowedRoles={["SUPER_ADMIN"]}
            >
              <LearningObjectivesPage />
            </ProtectedRoute>
          }
        />

        {/* Developer dashboard */}
        <Route
          path="developer"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <DeveloperPage />
            </ProtectedRoute>
          }
        />

        {/* Create variant */}
        <Route
          path="variants/new"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <VariantCreatePage />
            </ProtectedRoute>
          }
        />

        {/* Variant details */}
        <Route
          path="variants/:variantId"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <VariantDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Create question inside variant */}
        <Route
          path="variants/:variantId/questions/new"
          element={
            <ProtectedRoute
              allowedRoles={["DEVELOPER"]}
            >
              <QuestionEditorPage />
            </ProtectedRoute>
          }
        />

        {/* Edit question inside variant */}
        <Route
          path="variants/:variantId/questions/:questionId/edit"
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
          path="verifier"
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
          path="curator"
          element={
            <ProtectedRoute
              allowedRoles={["CURATOR"]}
            >
              <CuratorPage />
            </ProtectedRoute>
          }
        />

        {/* Legacy shared question view */}
        <Route
          path="questions/:id"
          element={
            <ProtectedRoute>
              <QuestionViewPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Catch-all */}
      <Route
        path="*"
        element={
          <Navigate
            to="/"
            replace
          />
        }
      />
    </Routes>
  );
}