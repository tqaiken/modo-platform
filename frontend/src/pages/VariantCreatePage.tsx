import {
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  BookOpen,
  GraduationCap,
  Save,
} from "lucide-react";
import {
  Link,
  useNavigate,
} from "react-router-dom";
import toast from "react-hot-toast";

import { api } from "../services/api";
import { useAuth } from "../contexts/AuthContext";


interface Subject {
  id: number;
  code: string;
  title: string;
  title_kz: string | null;
  is_active: boolean;
}


interface CreatedVariant {
  id: number;
  title: string;
  description: string | null;
  grade: number;
  subject_id: number | null;
  developer_id: number;
  status: "DRAFT";
  question_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  published_at: string | null;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const GRADES = Array.from(
  {
    length: 12,
  },
  (_, index) => index + 1
);


function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  const apiError = error as ApiError;
  const detail =
    apiError.response?.data?.detail;

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

  if (
    typeof detail === "object" &&
    detail !== null &&
    "message" in detail
  ) {
    return String(
      (
        detail as {
          message: unknown;
        }
      ).message
    );
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}


export default function VariantCreatePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] =
    useState("");

  const [description, setDescription] =
    useState("");

  const [grade, setGrade] =
    useState("");

  const [
    subjectTitle,
    setSubjectTitle,
  ] = useState("Загрузка...");

  const [
    loadingSubject,
    setLoadingSubject,
  ] = useState(true);

  const [saving, setSaving] =
    useState(false);


  useEffect(() => {
    const loadSubject =
      async (): Promise<void> => {
        if (
          user?.subject_id === null ||
          user?.subject_id === undefined
        ) {
          setSubjectTitle(
            "Предмет не назначен"
          );

          setLoadingSubject(false);
          return;
        }

        try {
          const response =
            await api.get<Subject[]>(
              "/api/v1/subjects"
            );

          const subject =
            response.data.find(
              (item) =>
                item.id ===
                user.subject_id
            );

          setSubjectTitle(
            subject?.title ??
              `Предмет #${user.subject_id}`
          );
        } catch (error: unknown) {
          setSubjectTitle(
            "Не удалось загрузить предмет"
          );

          toast.error(
            getErrorMessage(
              error,
              "Не удалось загрузить предмет разработчика."
            )
          );
        } finally {
          setLoadingSubject(false);
        }
      };

    void loadSubject();
  }, [user?.subject_id]);


  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (
      user?.subject_id === null ||
      user?.subject_id === undefined
    ) {
      toast.error(
        "Для вашей учётной записи не назначен предмет."
      );

      return;
    }

    const normalizedTitle =
      title.trim();

    if (normalizedTitle.length < 2) {
      toast.error(
        "Название варианта должно содержать минимум два символа."
      );

      return;
    }

    if (!grade) {
      toast.error(
        "Выберите класс."
      );

      return;
    }

    const numericGrade =
      Number(grade);

    if (
      !Number.isInteger(numericGrade) ||
      numericGrade < 1 ||
      numericGrade > 12
    ) {
      toast.error(
        "Класс должен быть числом от 1 до 12."
      );

      return;
    }

    setSaving(true);

    try {
      const response =
        await api.post<CreatedVariant>(
          "/api/v1/variants",
          {
            title: normalizedTitle,
            description:
              description.trim() ||
              null,
            grade: numericGrade,
          }
        );

      toast.success(
        `${numericGrade} класс: вариант создан.`
      );

      navigate(
        `/variants/${response.data.id}`,
        {
          replace: true,
        }
      );
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось создать вариант."
        )
      );
    } finally {
      setSaving(false);
    }
  };


  const subjectMissing =
    user?.subject_id === null ||
    user?.subject_id === undefined;

  const formInvalid =
    saving ||
    loadingSubject ||
    subjectMissing ||
    title.trim().length < 2 ||
    !grade;


  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <Link
          to="/developer"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад к вариантам
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Новый вариант
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Укажите класс и создайте вариант,
          затем добавьте в него вопросы
        </p>
      </div>

      {subjectMissing && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Для вашей учётной записи не назначен
          предмет. Обратитесь к
          супер-администратору.
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="card space-y-5"
      >
        <div>
          <label
            htmlFor="subject"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Предмет
          </label>

          <div className="relative">
            <BookOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

            <input
              id="subject"
              type="text"
              value={subjectTitle}
              className="input-field cursor-not-allowed bg-gray-50 pl-10 text-gray-600"
              disabled
              readOnly
            />
          </div>

          <p className="mt-1.5 text-xs text-gray-500">
            Предмет назначается
            супер-администратором и не может
            быть изменён разработчиком.
          </p>
        </div>

        <div>
          <label
            htmlFor="grade"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Класс
            <span className="ml-1 text-red-500">
              *
            </span>
          </label>

          <div className="relative">
            <GraduationCap className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

            <select
              id="grade"
              value={grade}
              onChange={(event) => {
                setGrade(
                  event.target.value
                );
              }}
              className="input-field pl-10"
              disabled={
                saving ||
                subjectMissing
              }
              required
            >
              <option value="">
                Выберите класс
              </option>

              {GRADES.map(
                (gradeNumber) => (
                  <option
                    key={gradeNumber}
                    value={gradeNumber}
                  >
                    {gradeNumber} класс
                  </option>
                )
              )}
            </select>
          </div>

          <p className="mt-1.5 text-xs text-gray-500">
            Класс применяется ко всему варианту
            и будет отображаться в очередях,
            банке, PDF и Excel.
          </p>
        </div>

        <div>
          <label
            htmlFor="title"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Название варианта
            <span className="ml-1 text-red-500">
              *
            </span>
          </label>

          <input
            id="title"
            type="text"
            value={title}
            onChange={(event) => {
              setTitle(
                event.target.value
              );
            }}
            className="input-field"
            placeholder="Например: Вариант 1"
            minLength={2}
            maxLength={500}
            disabled={saving}
            required
            autoFocus
          />

          <p className="mt-1.5 text-xs text-gray-500">
            Предмет и класс уже заданы отдельно,
            поэтому достаточно указать название
            или номер варианта.
          </p>
        </div>

        <div>
          <label
            htmlFor="description"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Описание, необязательно
          </label>

          <textarea
            id="description"
            value={description}
            onChange={(event) => {
              setDescription(
                event.target.value
              );
            }}
            className="input-field min-h-28 resize-y"
            placeholder="Краткое служебное описание варианта"
            maxLength={2000}
            disabled={saving}
          />

          <p className="mt-1 text-right text-xs text-gray-400">
            {description.length} / 2000
          </p>
        </div>

        <div className="flex flex-wrap gap-3 border-t border-gray-200 pt-5">
          <button
            type="submit"
            disabled={formInvalid}
            className="btn-primary"
          >
            <Save className="h-4 w-4" />

            {saving
              ? "Создание..."
              : "Создать вариант"}
          </button>

          <Link
            to="/developer"
            className="btn-secondary"
          >
            Отмена
          </Link>
        </div>
      </form>
    </div>
  );
}