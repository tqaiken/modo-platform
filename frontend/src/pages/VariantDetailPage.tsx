import {
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  ArrowLeft,
  BookOpen,
  FileQuestion,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  Link,
  useParams,
} from "react-router-dom";
import toast from "react-hot-toast";

import { api } from "../services/api";


type VariantStatus =
  | "DRAFT"
  | "VERIFICATION"
  | "REVISION"
  | "APPROVED"
  | "IN_BANK";


type CognitiveLevel =
  | "BASIC"
  | "MEDIUM"
  | "HIGH";


interface Variant {
  id: number;
  title: string;
  description: string | null;
  subject_id: number | null;
  developer_id: number;
  status: VariantStatus;
  question_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}


interface VariantQuestion {
  id: number;
  variant_id: number | null;
  order_number: number;
  learning_objective_id: number | null;
  cognitive_level: CognitiveLevel | null;
  resource_kz: string | null;
  resource_ru: string | null;
  question_text_kz: string | null;
  question_text_ru: string | null;
  options: Array<Record<string, unknown>>;
  explanation_kz: string | null;
  explanation_ru: string | null;
  subject_id: number | null;
  status: string;
  author_id: number;
  reviewer_id: number | null;
  media_files: Array<Record<string, unknown>>;
  comments: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}


interface VariantQuestionList {
  items: VariantQuestion[];
  total: number;
}


interface Subject {
  id: number;
  code: string;
  title: string;
  title_kz: string | null;
  is_active: boolean;
}


interface LearningObjective {
  id: number;
  subject_id: number;
  code: string;
  title_kz: string;
  title_ru: string;
  is_active: boolean;
}


interface LearningObjectiveList {
  items: LearningObjective[];
  total: number;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const STATUS_LABELS: Record<VariantStatus, string> = {
  DRAFT: "Черновик",
  VERIFICATION: "На верификации",
  REVISION: "На доработке",
  APPROVED: "Утверждён",
  IN_BANK: "В банке",
};


const STATUS_CLASSES: Record<VariantStatus, string> = {
  DRAFT: "badge bg-gray-100 text-gray-700",
  VERIFICATION: "badge bg-blue-100 text-blue-800",
  REVISION: "badge bg-amber-100 text-amber-800",
  APPROVED: "badge bg-green-100 text-green-800",
  IN_BANK: "badge bg-purple-100 text-purple-800",
};


const COGNITIVE_LEVEL_LABELS: Record<
  CognitiveLevel,
  string
> = {
  BASIC: "Базовый, знание и понимание",
  MEDIUM: "Средний, применение и анализ",
  HIGH: "Высокий, синтез и оценка",
};


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


export default function VariantDetailPage() {
  const { variantId } = useParams<{
    variantId: string;
  }>();

  const [variant, setVariant] =
    useState<Variant | null>(null);

  const [questions, setQuestions] =
    useState<VariantQuestion[]>([]);

  const [subjects, setSubjects] =
    useState<Subject[]>([]);

  const [objectives, setObjectives] =
    useState<LearningObjective[]>([]);

  const [loading, setLoading] = useState(true);

  const numericVariantId = Number(variantId);


  const loadData = useCallback(
    async (): Promise<void> => {
      if (
        !Number.isInteger(numericVariantId) ||
        numericVariantId < 1
      ) {
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const [
          variantResponse,
          questionsResponse,
          subjectsResponse,
          objectivesResponse,
        ] = await Promise.all([
          api.get<Variant>(
            `/api/v1/variants/${numericVariantId}`
          ),

          api.get<VariantQuestionList>(
            `/api/v1/variants/${numericVariantId}/questions`
          ),

          api.get<Subject[]>(
            "/api/v1/subjects"
          ),

          api.get<LearningObjectiveList>(
            "/api/v1/learning-objectives"
          ),
        ]);

        setVariant(variantResponse.data);
        setQuestions(
          questionsResponse.data.items
        );
        setSubjects(subjectsResponse.data);
        setObjectives(
          objectivesResponse.data.items
        );
      } catch (error: unknown) {
        toast.error(
          getErrorMessage(
            error,
            "Не удалось загрузить вариант."
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [numericVariantId]
  );


  useEffect(() => {
    void loadData();
  }, [loadData]);


  const getSubjectTitle = (
    subjectId: number | null
  ): string => {
    if (subjectId === null) {
      return "Предмет не назначен";
    }

    const subject = subjects.find(
      (item) => item.id === subjectId
    );

    return subject?.title ??
      `Предмет #${subjectId}`;
  };


  const getObjectiveLabel = (
    objectiveId: number | null
  ): string => {
    if (objectiveId === null) {
      return "ОРО не назначен";
    }

    const objective = objectives.find(
      (item) => item.id === objectiveId
    );

    if (!objective) {
      return `ОРО #${objectiveId}`;
    }

    return `${objective.code}: ${objective.title_ru}`;
  };


  const handleDeleteQuestion = async (
    question: VariantQuestion
  ): Promise<void> => {
    if (!variant) {
      return;
    }

    const confirmed = window.confirm(
      `Удалить вопрос №${question.order_number}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(
        `/api/v1/variants/${variant.id}/questions/${question.id}`
      );

      toast.success("Вопрос удалён.");

      await loadData();
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось удалить вопрос."
        )
      );
    }
  };


  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }


  if (
    !Number.isInteger(numericVariantId) ||
    numericVariantId < 1
  ) {
    return (
      <MessageCard
        title="Некорректный номер варианта"
        description="Проверьте адрес страницы."
      />
    );
  }


  if (!variant) {
    return (
      <MessageCard
        title="Вариант не найден"
        description="Вариант отсутствует или у вас нет доступа."
      />
    );
  }


  const editable =
    variant.status === "DRAFT" ||
    variant.status === "REVISION";


  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/developer"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад к вариантам
        </Link>
      </div>


      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">
                {variant.title}
              </h1>

              <span
                className={
                  STATUS_CLASSES[variant.status]
                }
              >
                {STATUS_LABELS[variant.status]}
              </span>
            </div>

            {variant.description && (
              <p className="mt-2 max-w-3xl text-sm text-gray-600">
                {variant.description}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              void loadData();
            }}
            className="btn-secondary"
          >
            <RefreshCw className="h-4 w-4" />
            Обновить
          </button>
        </div>


        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <InfoCard
            label="Номер варианта"
            value={`#${variant.id}`}
          />

          <InfoCard
            label="Предмет"
            value={getSubjectTitle(
              variant.subject_id
            )}
            icon={
              <BookOpen className="h-4 w-4" />
            }
          />

          <InfoCard
            label="Количество вопросов"
            value={String(questions.length)}
            icon={
              <FileQuestion className="h-4 w-4" />
            }
          />

          <InfoCard
            label="Режим"
            value={
              editable
                ? "Редактирование доступно"
                : "Только просмотр"
            }
          />
        </div>
      </section>


      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Вопросы варианта
          </h2>

          <p className="mt-1 text-sm text-gray-500">
            Вопросы отображаются в порядке прохождения
          </p>
        </div>

        {editable && (
          <Link
            to={`/variants/${variant.id}/questions/new`}
            className="btn-primary"
          >
            <Plus className="h-4 w-4" />
            Добавить вопрос
          </Link>
        )}
      </section>


      {!editable && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
          Вариант уже отправлен на проверку или утверждён.
          Редактирование вопросов недоступно.
        </div>
      )}


      {questions.length === 0 ? (
        <section className="card py-12 text-center">
          <FileQuestion className="mx-auto h-12 w-12 text-gray-300" />

          <h3 className="mt-4 text-lg font-semibold text-gray-900">
            В варианте пока нет вопросов
          </h3>

          <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">
            Добавьте первый двуязычный вопрос.
            Номер будет назначен автоматически.
          </p>

          {editable && (
            <Link
              to={`/variants/${variant.id}/questions/new`}
              className="btn-primary mt-5"
            >
              <Plus className="h-4 w-4" />
              Добавить первый вопрос
            </Link>
          )}
        </section>
      ) : (
        <div className="space-y-4">
          {questions.map((question) => (
            <article
              key={question.id}
              className="card"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700">
                      {question.order_number}
                    </span>

                    <div>
                      <h3 className="font-semibold text-gray-900">
                        Вопрос №{question.order_number}
                      </h3>

                      <p className="text-xs text-gray-500">
                        ID: {question.id}
                      </p>
                    </div>
                  </div>


                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <QuestionTextBlock
                      label="Қазақша"
                      value={
                        question.question_text_kz
                      }
                    />

                    <QuestionTextBlock
                      label="Русский"
                      value={
                        question.question_text_ru
                      }
                    />
                  </div>


                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="badge bg-indigo-100 text-indigo-800">
                      {question.cognitive_level
                        ? COGNITIVE_LEVEL_LABELS[
                            question.cognitive_level
                          ]
                        : "Уровень не указан"}
                    </span>

                    <span className="badge bg-gray-100 text-gray-700">
                      {getObjectiveLabel(
                        question.learning_objective_id
                      )}
                    </span>

                    <span className="badge bg-gray-100 text-gray-700">
                      Ответов: {question.options.length}
                    </span>

                    {question.media_files.length > 0 && (
                      <span className="badge bg-blue-100 text-blue-800">
                        Файлов:{" "}
                        {question.media_files.length}
                      </span>
                    )}
                  </div>
                </div>


                {editable && (
                  <div className="flex shrink-0 gap-2">
                    <Link
                      to={`/variants/${variant.id}/questions/${question.id}/edit`}
                      className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50"
                    >
                      <Pencil className="h-4 w-4" />
                      Изменить
                    </Link>

                    <button
                      type="button"
                      onClick={() => {
                        void handleDeleteQuestion(
                          question
                        );
                      }}
                      className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                      Удалить
                    </button>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}


function InfoCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-gray-500">
        {icon}
        {label}
      </div>

      <p className="mt-2 text-sm font-semibold text-gray-900">
        {value}
      </p>
    </div>
  );
}


function QuestionTextBlock({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {label}
      </p>

      <p className="line-clamp-4 whitespace-pre-wrap text-sm text-gray-700">
        {value || "Текст не заполнен"}
      </p>
    </div>
  );
}


function MessageCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="card py-12 text-center">
      <FileQuestion className="mx-auto h-12 w-12 text-gray-300" />

      <h1 className="mt-4 text-lg font-semibold text-gray-900">
        {title}
      </h1>

      <p className="mt-2 text-sm text-gray-500">
        {description}
      </p>

      <Link
        to="/developer"
        className="btn-primary mt-5"
      >
        Вернуться к вариантам
      </Link>
    </section>
  );
}