import {
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  BookOpen,
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
  subject_id: number | null;
  developer_id: number;
  status: "DRAFT";
  question_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  const apiError = error as ApiError;
  const detail = apiError.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  return fallback;
}


export default function VariantCreatePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [subjectTitle, setSubjectTitle] =
    useState("Загрузка...");

  const [loadingSubject, setLoadingSubject] =
    useState(true);

  const [saving, setSaving] = useState(false);


  useEffect(() => {
    const loadSubject = async (): Promise<void> => {
      if (user?.subject_id === null) {
        setSubjectTitle("Предмет не назначен");
        setLoadingSubject(false);
        return;
      }

      try {
        const response = await api.get<Subject[]>(
          "/api/v1/subjects"
        );

        const subject = response.data.find(
          (item) => item.id === user?.subject_id
        );

        setSubjectTitle(
          subject?.title ??
            `Предмет #${user?.subject_id}`
        );
      } catch (error: unknown) {
        setSubjectTitle("Не удалось загрузить предмет");

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

    if (user?.subject_id === null) {
      toast.error(
        "Для вашей учётной записи не назначен предмет."
      );
      return;
    }

    setSaving(true);

    try {
      const response = await api.post<CreatedVariant>(
        "/api/v1/variants",
        {
          title: title.trim(),
          description:
            description.trim() || null,
        }
      );

      toast.success("Вариант создан.");

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
    user?.subject_id === null;


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
          Создайте вариант, затем добавьте в него вопросы
        </p>
      </div>

      {subjectMissing && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Для вашей учётной записи не назначен предмет.
          Обратитесь к супер-администратору.
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
            Предмет назначается супер-администратором
            и не может быть изменён разработчиком.
          </p>
        </div>

        <div>
          <label
            htmlFor="title"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Название варианта
          </label>

          <input
            id="title"
            type="text"
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
            }}
            className="input-field"
            placeholder="Например: Математика, вариант 1"
            minLength={2}
            maxLength={500}
            required
            autoFocus
          />

          <p className="mt-1.5 text-xs text-gray-500">
            Это название всего варианта, а не отдельного
            вопроса.
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
              setDescription(event.target.value);
            }}
            className="input-field min-h-28 resize-y"
            placeholder="Краткое служебное описание варианта"
            maxLength={2000}
          />

          <p className="mt-1 text-right text-xs text-gray-400">
            {description.length} / 2000
          </p>
        </div>

        <div className="flex flex-wrap gap-3 border-t border-gray-200 pt-5">
          <button
            type="submit"
            disabled={
              saving ||
              loadingSubject ||
              subjectMissing ||
              title.trim().length < 2
            }
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