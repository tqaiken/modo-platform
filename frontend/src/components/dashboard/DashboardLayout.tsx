import { createElement } from "react";
import {
  Link,
  Outlet,
  useLocation,
} from "react-router-dom";
import { clsx } from "clsx";
import {
  FileEdit,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "../../contexts/AuthContext";


type NavigationItem = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
};


const ROLE_NAV: Record<string, NavigationItem[]> = {
  SUPER_ADMIN: [
    {
      to: "/admin",
      label: "Панель управления",
      icon: LayoutDashboard,
    },
  ],

  DEVELOPER: [
    {
      to: "/developer",
      label: "Мои вопросы",
      icon: FileEdit,
    },
    {
      to: "/questions/new",
      label: "Новый вопрос",
      icon: FileEdit,
    },
  ],

  VERIFIER: [
    {
      to: "/verifier",
      label: "Очередь проверки",
      icon: ShieldCheck,
    },
  ],

  CURATOR: [
    {
      to: "/curator",
      label: "Банк заданий",
      icon: FolderOpen,
    },
  ],
};


const ROLE_LABELS: Record<string, string> = {
  SUPER_ADMIN: "Супер-администратор",
  DEVELOPER: "Разработчик",
  VERIFIER: "Верификатор",
  CURATOR: "Куратор",
};


const LOGO_SRC = "/logo.png";


export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (user === null) {
    return null;
  }

  const currentUser = user;
  const navItems = ROLE_NAV[currentUser.role] ?? [];


  const isRouteActive = (path: string): boolean => {
    if (location.pathname === path) {
      return true;
    }

    return (
      path !== "/" &&
      location.pathname.startsWith(`${path}/`)
    );
  };


  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-gray-200 bg-white">
        {/* Logo */}
        <div className="flex min-h-20 items-center gap-3 border-b border-gray-200 px-5">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white">
            {createElement("img", {
              src: LOGO_SRC,
              alt: "Логотип МОДО",
              className: "h-full w-full object-contain",
            })}
          </div>

          <div className="min-w-0">
            <p className="text-lg font-bold text-gray-900">
              МОДО
            </p>

            <p className="truncate text-xs text-gray-500">
              Банк тестовых заданий
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = isRouteActive(item.to);

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
                <Icon className="h-5 w-5 shrink-0" />

                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User information */}
        <div className="border-t border-gray-200 p-4">
          <div className="mb-3">
            <p className="truncate text-sm font-medium text-gray-900">
              {currentUser.full_name}
            </p>

            <p className="truncate text-xs text-gray-500">
              {currentUser.email}
            </p>

            <span className="badge mt-2 bg-primary-100 text-primary-800">
              {ROLE_LABELS[currentUser.role] ??
                currentUser.role}
            </span>
          </div>

          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <LogOut className="h-4 w-4" />

            <span>Выйти</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1 overflow-auto">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}