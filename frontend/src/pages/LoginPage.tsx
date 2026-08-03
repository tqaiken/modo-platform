import {
  createElement,
  useState,
  type FormEvent,
} from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  Lock,
  UserRound,
} from "lucide-react";
import toast from "react-hot-toast";

import { useAuth } from "../contexts/AuthContext";

const LOGO_SRC = "/logo.png";

type ApiError = {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await login(username, password);

      toast.success("Добро пожаловать!");

      navigate("/", {
        replace: true,
      });
    } catch (requestError: unknown) {
      const apiError = requestError as ApiError;
      const detail = apiError.response?.data?.detail;

      const message =
        typeof detail === "string"
          ? detail
          : "Неверный логин или пароль.";

      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-20 w-40 items-center justify-center overflow-hidden rounded-2xl bg-white px-4 shadow-lg">
            {createElement("img", {
              src: LOGO_SRC,
              alt: "Логотип МОДО",
              className: "max-h-full max-w-full object-contain",
            })}
          </div>

          <h1 className="text-2xl font-bold leading-tight text-gray-900">
            Мониторинг образовательных достижений обучающихся
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            Платформа разработки тестовых заданий
          </p>
        </div>

        <div className="card">
          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >
            {error && (
              <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label
                htmlFor="username"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Логин
              </label>

              <div className="relative">
                <UserRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

                <input
                  id="username"
                  name="username"
                  type="text"
                  value={username}
                  onChange={(event) => {
                    setUsername(event.target.value);
                  }}
                  className="input-field pl-10"
                  placeholder="Введите логин"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  minLength={3}
                  maxLength={100}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Пароль
              </label>

              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

                <input
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                  }}
                  className="input-field pl-10"
                  placeholder="Введите пароль"
                  autoComplete="current-password"
                  minLength={8}
                  maxLength={128}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                username.trim().length < 3 ||
                password.length < 8
              }
              className="btn-primary w-full"
            >
              {loading
                ? "Выполняется вход..."
                : "Войти"}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-gray-500">
            Учётные записи создаёт супер-администратор
          </p>
        </div>
      </div>
    </div>
  );
}