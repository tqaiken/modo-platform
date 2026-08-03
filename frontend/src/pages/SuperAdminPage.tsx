import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Plus,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  Users,
} from "lucide-react";
import toast from "react-hot-toast";

import { api } from "../services/api";


type UserRole =
  | "SUPER_ADMIN"
  | "CURATOR"
  | "VERIFIER"
  | "DEVELOPER";


interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  subject_id: number | null;
}


interface Subject {
  id: number;
  code: string;
  title: string;
  title_kz: string | null;
  is_active: boolean;
}


interface UserForm {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  subject_id: string;
}


interface SubjectForm {
  code: string;
  title: string;
  title_kz: string;
}


const INITIAL_USER_FORM: UserForm = {
  email: "",
  full_name: "",
  password: "",
  role: "DEVELOPER",
  subject_id: "",
};


const INITIAL_SUBJECT_FORM: SubjectForm = {
  code: "",
  title: "",
  title_kz: "",
};


const ROLE_LABELS: Record<UserRole, string> = {
  SUPER_ADMIN: "Супер-администратор",
  CURATOR: "Куратор",
  VERIFIER: "Верификатор",
  DEVELOPER: "Разработчик",
};


const SUBJECT_REQUIRED_ROLES: UserRole[] = [
  "DEVELOPER",
  "VERIFIER",
];


export default function SuperAdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  const [userForm, setUserForm] =
    useState<UserForm>(INITIAL_USER_FORM);

  const [subjectForm, setSubjectForm] =
    useState<SubjectForm>(INITIAL_SUBJECT_FORM);

  const [loading, setLoading] = useState(true);
  const [creatingUser, setCreatingUser] = useState(false);
  const [creatingSubject, setCreatingSubject] = useState(false);

  const roleNeedsSubject = SUBJECT_REQUIRED_ROLES.includes(
    userForm.role
  );


  const loadData = async () => {
    setLoading(true);

    try {
      const [usersResponse, subjectsResponse] = await Promise.all([
        api.get<User[]>("/api/v1/auth/users"),
        api.get<Subject[]>("/api/v1/subjects"),
      ]);

      setUsers(usersResponse.data);
      setSubjects(subjectsResponse.data);
    } catch (error: any) {
      const message =
        error.response?.data?.detail ||
        "Не удалось загрузить данные панели.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadData();
  }, []);


  useEffect(() => {
    if (!roleNeedsSubject) {
      setUserForm((current) => ({
        ...current,
        subject_id: "",
      }));
    }
  }, [roleNeedsSubject]);


  const dashboard = useMemo(() => {
    return {
      total: users.length,

      developers: users.filter(
        (user) => user.role === "DEVELOPER"
      ).length,

      verifiers: users.filter(
        (user) => user.role === "VERIFIER"
      ).length,

      curators: users.filter(
        (user) => user.role === "CURATOR"
      ).length,

      withoutSubject: users.filter(
        (user) =>
          SUBJECT_REQUIRED_ROLES.includes(user.role) &&
          user.subject_id === null
      ).length,
    };
  }, [users]);


  const getSubjectTitle = (subjectId: number | null) => {
    if (subjectId === null) {
      return "Не назначен";
    }

    const subject = subjects.find(
      (item) => item.id === subjectId
    );

    return subject?.title || `Предмет #${subjectId}`;
  };


  const handleCreateSubject = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    setCreatingSubject(true);

    try {
      await api.post("/api/v1/subjects", {
        code: subjectForm.code.trim(),
        title: subjectForm.title.trim(),
        title_kz:
          subjectForm.title_kz.trim() || null,
      });

      toast.success("Предмет создан.");
      setSubjectForm(INITIAL_SUBJECT_FORM);

      await loadData();
    } catch (error: any) {
      const message =
        error.response?.data?.detail ||
        "Не удалось создать предмет.";

      toast.error(message);
    } finally {
      setCreatingSubject(false);
    }
  };


  const handleCreateUser = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (
      roleNeedsSubject &&
      !userForm.subject_id
    ) {
      toast.error(
        "Для разработчика и верификатора выберите предмет."
      );
      return;
    }

    setCreatingUser(true);

    try {
      await api.post("/api/v1/auth/users", {
        email: userForm.email.trim(),
        full_name: userForm.full_name.trim(),
        password: userForm.password,
        role: userForm.role,
        subject_id: roleNeedsSubject
          ? Number(userForm.subject_id)
          : null,
      });

      toast.success("Пользователь создан.");
      setUserForm(INITIAL_USER_FORM);

      await loadData();
    } catch (error: any) {
      const detail = error.response?.data?.detail;

      const message =
        typeof detail === "string"
          ? detail
          : "Не удалось создать пользователя.";

      toast.error(message);
    } finally {
      setCreatingUser(false);
    }
  };


  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Панель супер-администратора
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Управление пользователями, ролями и предметами
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              loading ? "animate-spin" : ""
            }`}
          />
          Обновить
        </button>
      </div>


      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <DashboardCard
          label="Всего пользователей"
          value={dashboard.total}
          icon={Users}
        />

        <DashboardCard
          label="Разработчики"
          value={dashboard.developers}
          icon={UserCheck}
        />

        <DashboardCard
          label="Верификаторы"
          value={dashboard.verifiers}
          icon={ShieldCheck}
        />

        <DashboardCard
          label="Кураторы"
          value={dashboard.curators}
          icon={Users}
        />

        <DashboardCard
          label="Без предмета"
          value={dashboard.withoutSubject}
          icon={BookOpen}
          warning={dashboard.withoutSubject > 0}
        />
      </section>


      <section className="grid gap-6 xl:grid-cols-2">
        <div className="card">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-gray-900">
              Новый предмет
            </h2>

            <p className="text-sm text-gray-500">
              Сначала создайте предмет, затем назначайте его
              разработчикам и верификаторам.
            </p>
          </div>

          <form
            onSubmit={handleCreateSubject}
            className="space-y-4"
          >
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Код предмета
              </label>

              <input
                value={subjectForm.code}
                onChange={(event) =>
                  setSubjectForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                className="input-field"
                placeholder="math"
                minLength={2}
                maxLength={50}
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Название на русском
              </label>

              <input
                value={subjectForm.title}
                onChange={(event) =>
                  setSubjectForm((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                className="input-field"
                placeholder="Математика"
                maxLength={255}
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Название на казахском
              </label>

              <input
                value={subjectForm.title_kz}
                onChange={(event) =>
                  setSubjectForm((current) => ({
                    ...current,
                    title_kz: event.target.value,
                  }))
                }
                className="input-field"
                placeholder="Математика"
                maxLength={255}
              />
            </div>

            <button
              type="submit"
              disabled={creatingSubject}
              className="btn-primary w-full"
            >
              <Plus className="h-4 w-4" />
              {creatingSubject
                ? "Создание..."
                : "Создать предмет"}
            </button>
          </form>
        </div>


        <div className="card">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-gray-900">
              Новый пользователь
            </h2>

            <p className="text-sm text-gray-500">
              Предмет обязателен для разработчика и
              верификатора.
            </p>
          </div>

          <form
            onSubmit={handleCreateUser}
            className="space-y-4"
          >
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                ФИО
              </label>

              <input
                value={userForm.full_name}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
                className="input-field"
                minLength={2}
                maxLength={255}
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Email
              </label>

              <input
                type="email"
                value={userForm.email}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }))
                }
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Временный пароль
              </label>

              <input
                type="password"
                value={userForm.password}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    password: event.target.value,
                  }))
                }
                className="input-field"
                minLength={8}
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Роль
              </label>

              <select
                value={userForm.role}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    role: event.target.value as UserRole,
                  }))
                }
                className="input-field"
              >
                <option value="DEVELOPER">
                  Разработчик
                </option>

                <option value="VERIFIER">
                  Верификатор
                </option>

                <option value="CURATOR">
                  Куратор
                </option>

                <option value="SUPER_ADMIN">
                  Супер-администратор
                </option>
              </select>
            </div>

            {roleNeedsSubject && (
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Предмет
                </label>

                <select
                  value={userForm.subject_id}
                  onChange={(event) =>
                    setUserForm((current) => ({
                      ...current,
                      subject_id: event.target.value,
                    }))
                  }
                  className="input-field"
                  required
                >
                  <option value="">
                    Выберите предмет
                  </option>

                  {subjects.map((subject) => (
                    <option
                      key={subject.id}
                      value={subject.id}
                    >
                      {subject.title}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={creatingUser}
              className="btn-primary w-full"
            >
              <Plus className="h-4 w-4" />
              {creatingUser
                ? "Создание..."
                : "Создать пользователя"}
            </button>
          </form>
        </div>
      </section>


      <section className="card overflow-hidden p-0">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Пользователи
          </h2>
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          </div>
        ) : users.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-500">
            Пользователи не найдены.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <TableHeader>Пользователь</TableHeader>
                  <TableHeader>Роль</TableHeader>
                  <TableHeader>Предмет</TableHeader>
                  <TableHeader>Статус</TableHeader>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-200 bg-white">
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-900">
                        {user.full_name}
                      </p>

                      <p className="text-xs text-gray-500">
                        {user.email}
                      </p>
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {ROLE_LABELS[user.role]}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {getSubjectTitle(user.subject_id)}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={
                          user.is_active
                            ? "badge bg-green-100 text-green-800"
                            : "badge bg-gray-100 text-gray-700"
                        }
                      >
                        {user.is_active
                          ? "Активен"
                          : "Отключён"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>


      <section className="card overflow-hidden p-0">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Предметы
          </h2>
        </div>

        {subjects.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-500">
            Предметы ещё не созданы.
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {subjects.map((subject) => (
              <div
                key={subject.id}
                className="flex items-center justify-between gap-4 px-6 py-4"
              >
                <div>
                  <p className="font-medium text-gray-900">
                    {subject.title}
                  </p>

                  <p className="text-sm text-gray-500">
                    Код: {subject.code}
                    {subject.title_kz
                      ? ` · KZ: ${subject.title_kz}`
                      : ""}
                  </p>
                </div>

                <span className="badge bg-green-100 text-green-800">
                  Активен
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}


function DashboardCard({
  label,
  value,
  icon: Icon,
  warning = false,
}: {
  label: string;
  value: number;
  icon: typeof Users;
  warning?: boolean;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div
        className={`flex h-11 w-11 items-center justify-center rounded-xl ${
          warning
            ? "bg-amber-100 text-amber-700"
            : "bg-primary-100 text-primary-700"
        }`}
      >
        <Icon className="h-5 w-5" />
      </div>

      <div>
        <p className="text-2xl font-bold text-gray-900">
          {value}
        </p>

        <p className="text-xs text-gray-500">
          {label}
        </p>
      </div>
    </div>
  );
}


function TableHeader({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
      {children}
    </th>
  );
}