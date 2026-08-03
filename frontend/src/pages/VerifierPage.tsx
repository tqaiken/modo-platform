import {
  createElement,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  FileQuestion,
  MessageSquare,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import toast from "react-hot-toast";

import { api } from "../services/api";

import "katex/dist/katex.min.css";


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


interface VariantQueueItem {
  id: number;
  title: string;
  description: string | null;
  subject_id: number | null;
  developer_id: number;
  developer_name: string;
  status: VariantStatus;
  question_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}


interface VariantQueueResponse {
  items: VariantQueueItem[];
  total: number;
  page: number;
  page_size: number;
}


interface BilingualOption {
  key: string;
  text_kz: string;
  text_ru: string;
  is_correct: boolean;
}


interface MediaFile {
  id: number;
  public_url: string;
  original_filename: string;
  content_type: string;
  file_size: number;
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
  options: BilingualOption[];
  explanation_kz: string | null;
  explanation_ru: string | null;
  subject_id: number | null;
  status: string;
  author_id: number;
  reviewer_id: number | null;
  media_files: MediaFile[];
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


const PAGE_SIZE = 20;


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

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}


export default function VerifierPage() {
  const [variants, setVariants] =
    useState<VariantQueueItem[]>([]);

  const [subjects, setSubjects] =
    useState<Subject[]>([]);

  const [objectives, setObjectives] =
    useState<LearningObjective[]>([]);

  const [questionsByVariant, setQuestionsByVariant] =
    useState<Record<number, VariantQuestion[]>>({});

  const [expandedVariantId, setExpandedVariantId] =
    useState<number | null>(null);

  const [loadingVariantId, setLoadingVariantId] =
    useState<number | null>(null);

  const [reviewComment, setReviewComment] =
    useState("");

  const [total, setTotal] =
    useState(0);

  const [page, setPage] =
    useState(1);

  const [loading, setLoading] =
    useState(true);

  const [reviewing, setReviewing] =
    useState(false);


  const loadQueue = useCallback(
    async (): Promise<void> => {
      setLoading(true);

      try {
        const [
          queueResponse,
          subjectsResponse,
          objectivesResponse,
        ] = await Promise.all([
          api.get<VariantQueueResponse>(
            "/api/v1/variants/verification-queue",
            {
              params: {
                page,
                page_size: PAGE_SIZE,
              },
            }
          ),

          api.get<Subject[]>(
            "/api/v1/subjects"
          ),

          api.get<LearningObjectiveList>(
            "/api/v1/learning-objectives"
          ),
        ]);

        setVariants(
          queueResponse.data.items
        );

        setTotal(
          queueResponse.data.total
        );

        setSubjects(
          subjectsResponse.data
        );

        setObjectives(
          objectivesResponse.data.items
        );
      } catch (error: unknown) {
        toast.error(
          getErrorMessage(
            error,
            "Не удалось загрузить очередь верификации."
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [page]
  );


  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);


  const getSubjectTitle = (
    subjectId: number | null
  ): string => {
    if (subjectId === null) {
      return "Предмет не назначен";
    }

    const subject = subjects.find(
      (item) =>
        item.id === subjectId
    );

    return (
      subject?.title ??
      `Предмет #${subjectId}`
    );
  };


  const getObjectiveLabel = (
    objectiveId: number | null
  ): string => {
    if (objectiveId === null) {
      return "ОРО не назначен";
    }

    const objective = objectives.find(
      (item) =>
        item.id === objectiveId
    );

    if (!objective) {
      return `ОРО #${objectiveId}`;
    }

    return (
      `${objective.code}: ` +
      objective.title_ru
    );
  };


  const loadVariantQuestions = async (
    variantId: number
  ): Promise<void> => {
    if (
      questionsByVariant[variantId] !== undefined
    ) {
      return;
    }

    setLoadingVariantId(variantId);

    try {
      const response =
        await api.get<VariantQuestionList>(
          `/api/v1/variants/${variantId}/verification-questions`
        );

      setQuestionsByVariant((current) => {
        const next = {
          ...current,
        };

        next[variantId] =
          response.data.items;

        return next;
      });
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось загрузить вопросы варианта."
        )
      );
    } finally {
      setLoadingVariantId(null);
    }
  };

  const toggleVariant = async (
    variantId: number
  ): Promise<void> => {
    if (
      expandedVariantId === variantId
    ) {
      setExpandedVariantId(null);
      setReviewComment("");
      return;
    }

    setExpandedVariantId(variantId);
    setReviewComment("");

    await loadVariantQuestions(
      variantId
    );
  };


  const handleReview = async (
    variantId: number,
    approved: boolean
  ): Promise<void> => {
    const normalizedComment =
      reviewComment.trim();

    if (!normalizedComment) {
      toast.error(
        "Добавьте комментарий к проверке."
      );
      return;
    }

    const actionLabel = approved
      ? "утвердить"
      : "вернуть на доработку";

    const confirmed = window.confirm(
      `Вы действительно хотите ${actionLabel} весь вариант?`
    );

    if (!confirmed) {
      return;
    }

    setReviewing(true);

    try {
      await api.post(
        `/api/v1/variants/${variantId}/review`,
        {
          approved,
          comment: normalizedComment,
        }
      );

      toast.success(
        approved
          ? "Вариант утверждён."
          : "Вариант возвращён на доработку."
      );

      setReviewComment("");
      setExpandedVariantId(null);

      setQuestionsByVariant(
        (current) => {
          const next = {
            ...current,
          };

          delete next[variantId];

          return next;
        }
      );

      await loadQueue();
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось выполнить проверку варианта."
        )
      );
    } finally {
      setReviewing(false);
    }
  };


  const totalPages = Math.max(
    1,
    Math.ceil(total / PAGE_SIZE)
  );


  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Очередь верификации
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Вариантов ожидают проверки: {total}
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            void loadQueue();
          }}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              loading
                ? "animate-spin"
                : ""
            }`}
          />

          Обновить
        </button>
      </div>


      <section className="card flex flex-wrap items-center gap-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
          <ClipboardCheck className="h-5 w-5" />
        </div>

        <div>
          <p className="font-semibold text-gray-900">
            Проверяется весь вариант
          </p>

          <p className="text-sm text-gray-500">
            Решение применяется одновременно
            ко всем вопросам варианта.
          </p>
        </div>
      </section>


      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : variants.length === 0 ? (
        <section className="card py-12 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-400" />

          <h2 className="mt-4 text-lg font-semibold text-gray-900">
            Очередь пуста
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Все отправленные варианты проверены.
          </p>
        </section>
      ) : (
        <div className="space-y-4">
          {variants.map((variant) => {
            const isExpanded =
              expandedVariantId ===
              variant.id;

            const variantQuestions =
              questionsByVariant[
                variant.id
              ] ?? [];

            const questionsLoading =
              loadingVariantId ===
              variant.id;

            return (
              <article
                key={variant.id}
                className="card overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => {
                    void toggleVariant(
                      variant.id
                    );
                  }}
                  className="flex w-full items-start justify-between gap-4 text-left"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-xs text-gray-400">
                        Вариант #{variant.id}
                      </span>

                      <span className="badge bg-blue-100 text-blue-800">
                        На верификации
                      </span>
                    </div>

                    <h2 className="mt-2 text-lg font-semibold text-gray-900">
                      {variant.title}
                    </h2>

                    {variant.description && (
                      <p className="mt-1 line-clamp-2 text-sm text-gray-600">
                        {variant.description}
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-500">
                      <span className="inline-flex items-center gap-1.5">
                        <BookOpen className="h-3.5 w-3.5" />
                        {getSubjectTitle(
                          variant.subject_id
                        )}
                      </span>

                      <span className="inline-flex items-center gap-1.5">
                        <FileQuestion className="h-3.5 w-3.5" />
                        Вопросов:{" "}
                        {variant.question_count}
                      </span>

                      <span>
                        Разработчик:{" "}
                        {variant.developer_name}
                      </span>

                      {variant.submitted_at && (
                        <span>
                          Отправлен:{" "}
                          {format(
                            new Date(
                              variant.submitted_at
                            ),
                            "d MMM yyyy, HH:mm",
                            {
                              locale: ru,
                            }
                          )}
                        </span>
                      )}
                    </div>
                  </div>

                  {isExpanded ? (
                    <ChevronUp className="mt-1 h-5 w-5 shrink-0 text-gray-400" />
                  ) : (
                    <ChevronDown className="mt-1 h-5 w-5 shrink-0 text-gray-400" />
                  )}
                </button>


                {isExpanded && (
                  <div className="mt-6 border-t border-gray-200 pt-6">
                    {questionsLoading ? (
                      <div className="flex h-36 items-center justify-center">
                        <div className="h-7 w-7 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
                      </div>
                    ) : variantQuestions.length ===
                      0 ? (
                      <div className="rounded-lg bg-amber-50 p-4 text-sm text-amber-800">
                        В варианте не найдены вопросы.
                      </div>
                    ) : (
                      <div className="space-y-6">
                        {variantQuestions.map(
                          (question) => (
                            <QuestionReviewCard
                              key={question.id}
                              question={question}
                              objectiveLabel={
                                getObjectiveLabel(
                                  question
                                    .learning_objective_id
                                )
                              }
                            />
                          )
                        )}
                      </div>
                    )}


                    <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-gray-500" />

                        <h3 className="text-sm font-semibold text-gray-800">
                          Рецензия на весь вариант
                        </h3>
                      </div>

                      <textarea
                        value={reviewComment}
                        onChange={(event) => {
                          setReviewComment(
                            event.target.value
                          );
                        }}
                        className="input-field min-h-32 resize-y"
                        placeholder="Укажите итоговый комментарий, замечания или основание для утверждения..."
                        minLength={1}
                        maxLength={5000}
                        disabled={reviewing}
                        required
                      />

                      <p className="mt-1 text-right text-xs text-gray-400">
                        {reviewComment.length} / 5000
                      </p>

                      <div className="mt-4 flex flex-wrap gap-3">
                        <button
                          type="button"
                          onClick={() => {
                            void handleReview(
                              variant.id,
                              true
                            );
                          }}
                          disabled={
                            reviewing ||
                            questionsLoading ||
                            variantQuestions.length ===
                              0 ||
                            !reviewComment.trim()
                          }
                          className="btn-primary bg-green-600 hover:bg-green-700"
                        >
                          <CheckCircle2 className="h-4 w-4" />

                          {reviewing
                            ? "Сохранение..."
                            : "Утвердить вариант"}
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            void handleReview(
                              variant.id,
                              false
                            );
                          }}
                          disabled={
                            reviewing ||
                            questionsLoading ||
                            variantQuestions.length ===
                              0 ||
                            !reviewComment.trim()
                          }
                          className="btn-danger"
                        >
                          <XCircle className="h-4 w-4" />
                          Вернуть на доработку
                        </button>
                      </div>

                      <p className="mt-3 text-xs text-gray-500">
                        Решение изменит статус
                        варианта и всех его вопросов.
                      </p>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}


      {total > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setExpandedVariantId(null);
              setReviewComment("");

              setPage((current) =>
                Math.max(
                  1,
                  current - 1
                )
              );
            }}
            disabled={page === 1}
            className="btn-secondary"
          >
            Назад
          </button>

          <span className="text-sm text-gray-500">
            Страница {page} из {totalPages}
          </span>

          <button
            type="button"
            onClick={() => {
              setExpandedVariantId(null);
              setReviewComment("");

              setPage((current) =>
                Math.min(
                  totalPages,
                  current + 1
                )
              );
            }}
            disabled={
              page >= totalPages
            }
            className="btn-secondary"
          >
            Вперёд
          </button>
        </div>
      )}
    </div>
  );
}


function QuestionReviewCard({
  question,
  objectiveLabel,
}: {
  question: VariantQuestion;
  objectiveLabel: string;
}) {
  const cognitiveLabel =
    question.cognitive_level
      ? COGNITIVE_LEVEL_LABELS[
          question.cognitive_level
        ]
      : "Уровень не указан";

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
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

        <div className="flex flex-wrap gap-2">
          <span className="badge bg-indigo-100 text-indigo-800">
            {cognitiveLabel}
          </span>

          <span className="badge bg-gray-100 text-gray-700">
            {objectiveLabel}
          </span>
        </div>
      </div>


      {(question.resource_kz ||
        question.resource_ru) && (
        <div className="mt-5">
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            Ресурсный блок
          </h4>

          <div className="grid gap-4 xl:grid-cols-2">
            <MarkdownBlock
              label="Қазақша"
              value={question.resource_kz}
            />

            <MarkdownBlock
              label="Русский"
              value={question.resource_ru}
            />
          </div>
        </div>
      )}


      <div className="mt-5">
        <h4 className="mb-3 text-sm font-semibold text-gray-800">
          Текст вопроса
        </h4>

        <div className="grid gap-4 xl:grid-cols-2">
          <MarkdownBlock
            label="Қазақша"
            value={question.question_text_kz}
          />

          <MarkdownBlock
            label="Русский"
            value={question.question_text_ru}
          />
        </div>
      </div>


      <div className="mt-5">
        <h4 className="mb-3 text-sm font-semibold text-gray-800">
          Варианты ответа
        </h4>

        <div className="space-y-3">
          {question.options.map(
            (option, index) => (
              <div
                key={
                  option.key ||
                  String(index)
                }
                className={`rounded-lg border p-4 ${
                  option.is_correct
                    ? "border-green-300 bg-green-50"
                    : "border-gray-200 bg-gray-50"
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                      option.is_correct
                        ? "bg-green-600 text-white"
                        : "bg-gray-200 text-gray-700"
                    }`}
                  >
                    {option.key}
                  </span>

                  <span className="text-sm font-medium text-gray-800">
                    Ответ {option.key}
                  </span>

                  {option.is_correct && (
                    <CheckCircle2 className="ml-auto h-5 w-5 text-green-600" />
                  )}
                </div>

                <div className="grid gap-3 xl:grid-cols-2">
                  <MarkdownBlock
                    label="KZ"
                    value={option.text_kz}
                    compact
                  />

                  <MarkdownBlock
                    label="RU"
                    value={option.text_ru}
                    compact
                  />
                </div>
              </div>
            )
          )}
        </div>
      </div>


      {(question.explanation_kz ||
        question.explanation_ru) && (
        <div className="mt-5">
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            Пояснение к ответу
          </h4>

          <div className="grid gap-4 xl:grid-cols-2">
            <MarkdownBlock
              label="Қазақша"
              value={question.explanation_kz}
            />

            <MarkdownBlock
              label="Русский"
              value={question.explanation_ru}
            />
          </div>
        </div>
      )}


      {question.media_files.length > 0 && (
        <div className="mt-5">
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            Изображения
          </h4>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {question.media_files.map(
              (media) => (
                <a
                  key={media.id}
                  href={media.public_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="overflow-hidden rounded-xl border border-gray-200 bg-gray-50 hover:border-primary-300"
                >
                  <div className="flex h-44 items-center justify-center p-3">
                    {createElement("img", {
                      src: media.public_url,
                      alt:
                        media.original_filename,
                      className:
                        "max-h-full max-w-full object-contain",
                    })}
                  </div>

                  <p className="truncate border-t border-gray-200 bg-white px-3 py-2 text-xs text-gray-500">
                    {
                      media.original_filename
                    }
                  </p>
                </a>
              )
            )}
          </div>
        </div>
      )}
    </section>
  );
}


function MarkdownBlock({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string | null;
  compact?: boolean;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {label}
      </p>

      {value?.trim() ? (
        <div
          className={`prose max-w-none overflow-auto ${
            compact
              ? "text-sm"
              : ""
          }`}
        >
          <ReactMarkdown
            remarkPlugins={[
              remarkGfm,
              remarkMath,
            ]}
            rehypePlugins={[
              rehypeKatex,
            ]}
          >
            {value}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-sm text-gray-400">
          Не заполнено
        </p>
      )}
    </div>
  );
}