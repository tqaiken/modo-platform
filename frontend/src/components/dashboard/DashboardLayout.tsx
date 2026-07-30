import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import {
  FileEdit,
  ShieldCheck,
  FolderOpen,
  LogOut,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";

const ROLE_NAV = {
  DEVELOPER: [
    { to: "/developer", label: "Мои вопросы", icon: FileEdit },
    { to: "/questions/new", label: "Новый вопрос", icon: FileEdit },
  ],
  VERIFIER: [
    { to: "/verifier", label: "Очередь проверки", icon: ShieldCheck },
  ],
  CURATOR: [
    { to: "/curator", label: "Банк заданий", icon: FolderOpen },
  ],
};

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (!user) return null;

  const navItems = ROLE_NAV[user.role] || [];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-gray-200 bg-white">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
          <Zap className="h-6 w-6 text-primary-600" />
          <span className="text-lg font-bold text-gray-900">TestForge</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-50 text-primary-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User info + Logout */}
        <div className="border-t border-gray-200 p-4">
          <div className="mb-3">
            <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
            <p className="text-xs text-gray-500">{user.email}</p>
            <span className="badge bg-primary-100 text-primary-800 mt-1">
              {user.role}
            </span>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
