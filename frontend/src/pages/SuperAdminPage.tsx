import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { Link } from "react-router-dom";

import {
  BookOpen,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Target,
  UserCheck,
  Users,
  X,
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
  username: string;
  email: string | null;
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


interface UserCreateForm {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  subject_id: string;
}


interface UserEditForm {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  subject_id: string;
  is_active: boolean;
}


interface SubjectForm {
  code: string;
  title: string;
  title_kz: string;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const INITIAL_USER_FORM: UserCreateForm = {
  username: "",
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


function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  const apiError = error as ApiError;
  const detail = apiError.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (
          typeof item === "object" &&
          item !== null &&
          "msg" in item
        ) {
          return String(item.msg);
        }

        return String(item);
      })
      .join("; ");
  }

  return fallback;
}


function normalizeOptionalEmail(
  email: string
): string | null {
  const normalized = email.trim().toLowerCase();

  return normalized || null;
}


export default function SuperAdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  const [userForm, setUserForm] =
    useState<UserCreateForm>(INITIAL_USER_FORM);

  const [subjectForm, setSubjectForm] =
    useState<SubjectForm>(INITIAL_SUBJECT_FORM);

  const [editingUserId, setEditingUserId] =
    useState<number | null>(null);

  const [editForm, setEditForm] =
    useState<UserEditForm | null>(null);

  const [loading, setLoading] = useState(true);
  const [creatingUser, setCreatingUser] = useState(false);
  const [creatingSubject, setCreatingSubject] =
    useState(false);
  const [savingUser, setSavingUser] = useState(false);


  const createRoleNeedsSubject =
    SUBJECT_REQUIRED_ROLES.includes(userForm.role);

  const editRoleNeedsSubject =
    editForm !== null &&
    SUBJECT_REQUIRED_ROLES.includes(editForm.role);


  const loadData = async (): Promise<void> => {
    setLoading(true);

    try {
      const [usersResponse, subjectsResponse] =
        await Promise.all([
          api.get<User[]>("/api/v1/auth/users"),
          api.get<Subject[]>("/api/v1/subjects"),
        ]);

      setUsers(usersResponse.data);
      setSubjects(subjectsResponse.data);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось загрузить данные панели."
        )
      );
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    void loadData();
  }, []);


  useEffect(() => {
    if (!createRoleNeedsSubject) {
      setUserForm((current) => ({
        ...current,
        subject_id: "",
      }));
    }
  }, [createRoleNeedsSubject]);


  useEffect(() => {
    if (
      editForm !== null &&
      !editRoleNeedsSubject &&
      editForm.subject_id !== ""
    ) {
      setEditForm((current) => {
        if (current === null) {
          return null;
        }

        return {
          ...current,
          subject_id: "",
        };
      });
    }
  }, [editForm, editRoleNeedsSubject]);


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


  const getSubjectTitle = (
    subjectId: number | null
  ): string => {
    if (subjectId === null) {
      return "Не назначен";
    }

    const subject = subjects.find(
      (item) => item.id === subjectId
    );

    return subject?.title ?? `Предмет #${subjectId}`;
  };


  const handleCreateSubject = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
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
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось создать предмет."
        )
      );
    } finally {
      setCreatingSubject(false);
    }
  };


  const handleCreateUser = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (
      createRoleNeedsSubject &&
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
        username: userForm.username
          .trim()
          .toLowerCase(),
        email: normalizeOptionalEmail(userForm.email),
        full_name: userForm.full_name.trim(),
        password: userForm.password,
        role: userForm.role,
        subject_id: createRoleNeedsSubject
          ? Number(userForm.subject_id)
          : null,
      });

      toast.success("Пользователь создан.");
      setUserForm(INITIAL_USER_FORM);

      await loadData();
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось создать пользователя."
        )
      );
    } finally {
      setCreatingUser(false);
    }
  };


  const beginEditUser = (user: User): void => {
    setEditingUserId(user.id);

    setEditForm({
      username: user.username,
      email: user.email ?? "",
      full_name: user.full_name,
      password: "",
      role: user.role,
      subject_id:
        user.subject_id === null
          ? ""
          : String(user.subject_id),
      is_active: user.is_active,
    });
  };


  const cancelEditUser = (): void => {
    setEditingUserId(null);
    setEditForm(null);
  };


  const handleUpdateUser = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (
      editingUserId === null ||
      editForm === null
    ) {
      return;
    }

    if (
      editRoleNeedsSubject &&
      !editForm.subject_id
    ) {
      toast.error(
        "Для разработчика и верификатора выберите предмет."
      );
      return;
    }

    setSavingUser(true);

    try {
      const payload: {
        username: string;
        email: string | null;
        full_name: string;
        role: UserRole;
        subject_id: number | null;
        is_active: boolean;
        password?: string;
      } = {
        username: editForm.username
          .trim()
          .toLowerCase(),
        email: normalizeOptionalEmail(editForm.email),
        full_name: editForm.full_name.trim(),
        role: editForm.role,
        subject_id: editRoleNeedsSubject
          ? Number(editForm.subject_id)
          : null,
        is_active: editForm.is_active,
      };

      if (editForm.password.trim()) {
        payload.password = editForm.password;
      }

      await api.patch(
        `/api/v1/auth/users/${editingUserId}`,
        payload
      );

      toast.success("Пользователь обновлён.");
      cancelEditUser();

      await loadData();
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось обновить пользователя."
        )
      );
    } finally {
      setSavingUser(false);
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
          onClick={() => {
            void loadData();
          }}
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

      <section className="card flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-100 text-primary-700">
            <Target className="h-5 w-5" />
          </div>

          <div>
            <h2 className="font-semibold text-gray-900">
              Ожидаемые результаты обучения
            </h2>

            <p className="text-sm text-gray-500">
              Создание и редактирование ОРО по предметам
            </p>
          </div>
        </div>

        <Link
          to="/admin/learning-objectives"
          className="btn-secondary"
        >
          Управление ОРО
        </Link>
      </section>

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
              Создайте предмет перед назначением
              разработчиков и верификаторов.
            </p>
          </div>

          <form
            onSubmit={handleCreateSubject}
            className="space-y-4"
          >
            <FormField label="Код предмета">
              <input
                value={subjectForm.code}
                onChange={(event) => {
                  setSubjectForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }));
                }}
                className="input-field"
                placeholder="math"
                minLength={2}
                maxLength={50}
                required
              />
            </FormField>

            <FormField label="Название на русском">
              <input
                value={subjectForm.title}
                onChange={(event) => {
                  setSubjectForm((current) => ({
                    ...current,
                    title: event.target.value,
                  }));
                }}
                className="input-field"
                placeholder="Математика"
                maxLength={255}
                required
              />
            </FormField>

            <FormField label="Название на казахском">
              <input
                value={subjectForm.title_kz}
                onChange={(event) => {
                  setSubjectForm((current) => ({
                    ...current,
                    title_kz: event.target.value,
                  }));
                }}
                className="input-field"
                placeholder="Математика"
                maxLength={255}
              />
            </FormField>

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
              Логин обязателен. Email можно не указывать.
            </p>
          </div>

          <form
            onSubmit={handleCreateUser}
            className="space-y-4"
          >
            <FormField label="Логин">
              <input
                value={userForm.username}
                onChange={(event) => {
                  setUserForm((current) => ({
                    ...current,
                    username: event.target.value,
                  }));
                }}
                className="input-field"
                placeholder="developer_math"
                autoCapitalize="none"
                spellCheck={false}
                minLength={3}
                maxLength={100}
                pattern="[A-Za-z0-9._-]+"
                required
              />
            </FormField>

            <FormField label="ФИО">
              <input
                value={userForm.full_name}
                onChange={(event) => {
                  setUserForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }));
                }}
                className="input-field"
                minLength={2}
                maxLength={255}
                required
              />
            </FormField>

            <FormField label="Email, необязательно">
              <input
                type="email"
                value={userForm.email}
                onChange={(event) => {
                  setUserForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }));
                }}
                className="input-field"
                placeholder="user@example.com"
              />
            </FormField>

            <FormField label="Временный пароль">
              <input
                type="password"
                value={userForm.password}
                onChange={(event) => {
                  setUserForm((current) => ({
                    ...current,
                    password: event.target.value,
                  }));
                }}
                className="input-field"
                minLength={8}
                maxLength={128}
                required
              />
            </FormField>

            <FormField label="Роль">
              <RoleSelect
                value={userForm.role}
                onChange={(role) => {
                  setUserForm((current) => ({
                    ...current,
                    role,
                  }));
                }}
              />
            </FormField>

            {createRoleNeedsSubject && (
              <FormField label="Предмет">
                <SubjectSelect
                  subjects={subjects}
                  value={userForm.subject_id}
                  onChange={(subjectId) => {
                    setUserForm((current) => ({
                      ...current,
                      subject_id: subjectId,
                    }));
                  }}
                />
              </FormField>
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


      {editForm !== null && (
        <section className="card border-2 border-primary-100">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Редактирование пользователя
              </h2>

              <p className="text-sm text-gray-500">
                Измените данные и нажмите «Сохранить».
              </p>
            </div>

            <button
              type="button"
              onClick={cancelEditUser}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900"
              aria-label="Закрыть редактирование"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <form
            onSubmit={handleUpdateUser}
            className="grid gap-4 md:grid-cols-2"
          >
            <FormField label="Логин">
              <input
                value={editForm.username}
                onChange={(event) => {
                  setEditForm((current) =>
                    current === null
                      ? null
                      : {
                          ...current,
                          username: event.target.value,
                        }
                  );
                }}
                className="input-field"
                autoCapitalize="none"
                spellCheck={false}
                minLength={3}
                maxLength={100}
                pattern="[A-Za-z0-9._-]+"
                required
              />
            </FormField>

            <FormField label="ФИО">
              <input
                value={editForm.full_name}
                onChange={(event) => {
                  setEditForm((current) =>
                    current === null
                      ? null
                      : {
                          ...current,
                          full_name: event.target.value,
                        }
                  );
                }}
                className="input-field"
                minLength={2}
                maxLength={255}
                required
              />
            </FormField>

            <FormField label="Email, необязательно">
              <input
                type="email"
                value={editForm.email}
                onChange={(event) => {
                  setEditForm((current) =>
                    current === null
                      ? null
                      : {
                          ...current,
                          email: event.target.value,
                        }
                  );
                }}
                className="input-field"
              />
            </FormField>

            <FormField label="Новый пароль, необязательно">
              <input
                type="password"
                value={editForm.password}
                onChange={(event) => {
                  setEditForm((current) =>
                    current === null
                      ? null
                      : {
                          ...current,
                          password: event.target.value,
                        }
                  );
                }}
                className="input-field"
                placeholder="Оставьте пустым без изменения"
                minLength={8}
                maxLength={128}
              />
            </FormField>

            <FormField label="Роль">
              <RoleSelect
                value={editForm.role}
                onChange={(role) => {
                  setEditForm((current) =>
                    current === null
                      ? null
                      : {
                          ...current,
                          role,
                        }
                  );
                }}
              />
            </FormField>

            {editRoleNeedsSubject && (
              <FormField label="Предмет">
                <SubjectSelect
                  subjects={subjects}
                  value={editForm.subject_id}
                  onChange={(subjectId) => {
                    setEditForm((current) =>
                      current === null
                        ? null
                        : {
                            ...current,
                            subject_id: subjectId,
                          }
                    );
                  }}
                />
              </FormField>
            )}

            <div className="md:col-span-2">
              <label className="flex items-center gap-3 rounded-lg border border-gray-200 p-3">
                <input
                  type="checkbox"
                  checked={editForm.is_active}
                  onChange={(event) => {
                    setEditForm((current) =>
                      current === null
                        ? null
                        : {
                            ...current,
                            is_active: event.target.checked,
                          }
                    );
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600"
                />

                <span className="text-sm font-medium text-gray-700">
                  Учётная запись активна
                </span>
              </label>
            </div>

            <div className="flex gap-3 md:col-span-2">
              <button
                type="submit"
                disabled={savingUser}
                className="btn-primary"
              >
                {savingUser
                  ? "Сохранение..."
                  : "Сохранить"}
              </button>

              <button
                type="button"
                onClick={cancelEditUser}
                className="btn-secondary"
              >
                Отмена
              </button>
            </div>
          </form>
        </section>
      )}


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
                  <TableHeader>Логин</TableHeader>
                  <TableHeader>Роль</TableHeader>
                  <TableHeader>Предмет</TableHeader>
                  <TableHeader>Статус</TableHeader>
                  <TableHeader>Действия</TableHeader>
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
                        {user.email ?? "Email не указан"}
                      </p>
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-700">
                      {user.username}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {ROLE_LABELS[user.role]}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {SUBJECT_REQUIRED_ROLES.includes(user.role)
                        ? getSubjectTitle(user.subject_id)
                        : "Не требуется"}
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

                    <td className="whitespace-nowrap px-6 py-4">
                      <button
                        type="button"
                        onClick={() => {
                          beginEditUser(user);
                        }}
                        className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50"
                      >
                        <Pencil className="h-4 w-4" />
                        Редактировать
                      </button>
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


function RoleSelect({
  value,
  onChange,
}: {
  value: UserRole;
  onChange: (role: UserRole) => void;
}) {
  return (
    <select
      value={value}
      onChange={(event) => {
        onChange(event.target.value as UserRole);
      }}
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
  );
}


function SubjectSelect({
  subjects,
  value,
  onChange,
}: {
  subjects: Subject[];
  value: string;
  onChange: (subjectId: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(event) => {
        onChange(event.target.value);
      }}
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
  );
}


function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-gray-700">
        {label}
      </label>

      {children}
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
  children: ReactNode;
}) {
  return (
    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
      {children}
    </th>
  );
}