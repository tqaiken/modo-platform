import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileQuestion,
  Library,
  MessageSquare,
  Package,
  RefreshCw,
  Search,
  Send,
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


type CuratorTab =
  | "queue"
  | "bank";


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


interface CuratorVariant {
  id: number;
  title: string;
  description: string | null;
  subject_id: number | null;
  developer_id: number;
  developer_name: string;
  status: VariantStatus;
  question_count: number;
  review_comment: string | null;
  reviewer_name: string | null;
  curator_comment?: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  published_at?: string | null;
}


interface CuratorVariantList {
  items: CuratorVariant[];
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

  if (
    typeof detail === "object" &&
    detail !== null &&
    "message" in detail
  ) {
    return String(
      (detail as { message: unknown })
        .message
    );
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}


function getDownloadFilename(
  contentDisposition: string | undefined
): string {
  if (!contentDisposition) {
    return (
      `modo_variants_${
        new Date()
          .toISOString()
          .slice(0, 10)
      }.zip`
    );
  }

  const utf8Match =
    contentDisposition.match(
      /filename\*=UTF-8''([^;]+)/i
    );

  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(
        utf8Match[1]
      );
    } catch {
      return utf8Match[1];
    }
  }

  const filenameMatch =
    contentDisposition.match(
      /filename="?([^";]+)"?/i
    );

  if (filenameMatch?.[1]) {
    return filenameMatch[1];
  }

  return (
    `modo_variants_${
      new Date()
        .toISOString()
        .slice(0, 10)
    }.zip`
  );
}


export default function CuratorPage() {
  const [activeTab, setActiveTab] =
    useState<CuratorTab>("queue");

  const [variants, setVariants] =
    useState<CuratorVariant[]>([]);

  const [subjects, setSubjects] =
    useState<Subject[]>([]);

  const [objectives, setObjectives] =
    useState<LearningObjective[]>([]);

  const [
    questionsByVariant,
    setQuestionsByVariant,
  ] = useState<
    Record<number, VariantQuestion[]>
  >({});

  const [
    expandedVariantId,
    setExpandedVariantId,
  ] = useState<number | null>(null);

  const [
    loadingVariantId,
    setLoadingVariantId,
  ] = useState<number | null>(null);

  const [
    publishingVariantId,
    setPublishingVariantId,
  ] = useState<number | null>(null);

  const [
    curatorComment,
    setCuratorComment,
  ] = useState("");

  const [
    selectedVariantIds,
    setSelectedVariantIds,
  ] = useState<Set<number>>(
    new Set()
  );

  const [search, setSearch] =
    useState("");

  const [page, setPage] =
    useState(1);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [exporting, setExporting] =
    useState(false);


  const visibleVariantIds = useMemo(
    () =>
      variants.map(
        (variant) => variant.id
      ),
    [variants]
  );


  const allVisibleSelected = useMemo(
    () =>
      visibleVariantIds.length > 0 &&
      visibleVariantIds.every(
        (variantId) =>
          selectedVariantIds.has(
            variantId
          )
      ),
    [
      visibleVariantIds,
      selectedVariantIds,
    ]
  );


  const loadVariants = useCallback(
    async (): Promise<void> => {
      setLoading(true);

      const endpoint =
        activeTab === "queue"
          ? "/api/v1/variants/curator-queue"
          : "/api/v1/variants/bank";

      try {
        const [
          variantsResponse,
          subjectsResponse,
          objectivesResponse,
        ] = await Promise.all([
          api.get<CuratorVariantList>(
            endpoint,
            {
              params: {
                page,
                page_size: PAGE_SIZE,
                search:
                  search.trim() ||
                  undefined,
              },
            }
          ),

          api.get<Subject[]>(
            "/api/v1/subjects"
          ),

          api.get<LearningObjectiveList>(
            "/api/v1/learning-objectives",
            {
              params: {
                include_inactive: true,
              },
            }
          ),
        ]);

        setVariants(
          variantsResponse.data.items
        );

        setTotal(
          variantsResponse.data.total
        );

        setSubjects(
          subjectsResponse.data
        );

        setObjectives(
          objectivesResponse.data.items
        );
      } catch (error: unknown) {
        setVariants([]);
        setTotal(0);

        toast.error(
          getErrorMessage(
            error,
            activeTab === "queue"
              ? "Не удалось загрузить очередь куратора."
              : "Не удалось загрузить банк вариантов."
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [
      activeTab,
      page,
      search,
    ]
  );


  useEffect(() => {
    void loadVariants();
  }, [loadVariants]);


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
    questionsByVariant[variantId] !==
    undefined
  ) {
    return;
  }

  setLoadingVariantId(variantId);

  try {
    const response =
      await api.get<VariantQuestionList>(
        `/api/v1/variants/${variantId}/curator-questions`
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
      expandedVariantId ===
      variantId
    ) {
      setExpandedVariantId(null);
      setCuratorComment("");
      return;
    }

    setExpandedVariantId(
      variantId
    );

    setCuratorComment("");

    await loadVariantQuestions(
      variantId
    );
  };


  const handlePublish = async (
    variant: CuratorVariant
  ): Promise<void> => {
    const normalizedComment =
      curatorComment.trim();

    if (!normalizedComment) {
      toast.error(
        "Добавьте комментарий к публикации."
      );
      return;
    }

    const questions =
      questionsByVariant[
        variant.id
      ] ?? [];

    if (questions.length === 0) {
      toast.error(
        "В варианте не найдены вопросы."
      );
      return;
    }

    const confirmed = window.confirm(
      "Добавить весь вариант в банк заданий?\n\n" +
        "После публикации вариант получит статус IN_BANK."
    );

    if (!confirmed) {
      return;
    }

    setPublishingVariantId(
      variant.id
    );

    try {
      await api.post(
        `/api/v1/variants/${variant.id}/publish`,
        {
          comment:
            normalizedComment,
        }
      );

      toast.success(
        "Вариант добавлен в банк заданий."
      );

      setExpandedVariantId(null);
      setCuratorComment("");

      setQuestionsByVariant(
        (current) => {
          const next = {
            ...current,
          };

          delete next[variant.id];

          return next;
        }
      );

      await loadVariants();
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось добавить вариант в банк."
        )
      );
    } finally {
      setPublishingVariantId(
        null
      );
    }
  };


  const toggleVariantSelection = (
    variantId: number
  ): void => {
    setSelectedVariantIds(
      (current) => {
        const next = new Set(
          current
        );

        if (next.has(variantId)) {
          next.delete(variantId);
        } else {
          next.add(variantId);
        }

        return next;
      }
    );
  };


  const toggleAllVisibleVariants =
    (): void => {
      setSelectedVariantIds(
        (current) => {
          const next = new Set(
            current
          );

          if (allVisibleSelected) {
            visibleVariantIds.forEach(
              (variantId) => {
                next.delete(variantId);
              }
            );
          } else {
            visibleVariantIds.forEach(
              (variantId) => {
                next.add(variantId);
              }
            );
          }

          return next;
        }
      );
    };


  const handleExportVariants =
    async (): Promise<void> => {
      const variantIds = Array.from(
        selectedVariantIds
      );

      if (variantIds.length === 0) {
        toast.error(
          "Выберите варианты для экспорта."
        );
        return;
      }

      setExporting(true);

      try {
        const response = await api.post(
          "/api/v1/export/variants/zip",
          {
            variant_ids: variantIds,
          },
          {
            responseType: "blob",
          }
        );

        const blob =
          response.data instanceof Blob
            ? response.data
            : new Blob(
                [response.data],
                {
                  type:
                    "application/zip",
                }
              );

        const downloadUrl =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement("a");

        link.href = downloadUrl;

        link.download =
          getDownloadFilename(
            response.headers[
              "content-disposition"
            ]
          );

        document.body.appendChild(
          link
        );

        link.click();
        link.remove();

        window.URL.revokeObjectURL(
          downloadUrl
        );

        toast.success(
          `Экспортировано вариантов: ${variantIds.length}`
        );
      } catch (error: unknown) {
        toast.error(
          getErrorMessage(
            error,
            "Не удалось экспортировать варианты."
          )
        );
      } finally {
        setExporting(false);
      }
    };


  const changeTab = (
    nextTab: CuratorTab
  ): void => {
    if (nextTab === activeTab) {
      return;
    }

    setActiveTab(nextTab);
    setPage(1);
    setSearch("");
    setExpandedVariantId(null);
    setCuratorComment("");
    setQuestionsByVariant({});
    setSelectedVariantIds(
      new Set()
    );
  };


  const changePage = (
    nextPage: number
  ): void => {
    setExpandedVariantId(null);
    setCuratorComment("");
    setPage(nextPage);
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
            Управление банком заданий
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Утверждённые варианты и опубликованный банк
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            void loadVariants();
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
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-100 text-purple-700">
          <Library className="h-5 w-5" />
        </div>

        <div>
          <p className="font-semibold text-gray-900">
            Публикуется весь вариант
          </p>

          <p className="text-sm text-gray-500">
            Вариант и все вложенные вопросы
            переходят в банк как единый комплект.
          </p>
        </div>
      </section>


      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
          <button
            type="button"
            onClick={() => {
              changeTab("queue");
            }}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
              activeTab === "queue"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <CheckCircle2 className="h-4 w-4" />
            Утверждённые
          </button>

          <button
            type="button"
            onClick={() => {
              changeTab("bank");
            }}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
              activeTab === "bank"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <Package className="h-4 w-4" />
            В банке
          </button>
        </div>

        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(
                event.target.value
              );

              setPage(1);
              setExpandedVariantId(null);
              setCuratorComment("");
              setSelectedVariantIds(
                new Set()
              );
            }}
            className="input-field pl-10"
            placeholder="Поиск по названию варианта"
          />
        </div>
      </div>


      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {activeTab === "queue"
              ? "Очередь куратора"
              : "Опубликованные варианты"}
          </h2>

          <p className="mt-1 text-sm text-gray-500">
            Всего: {total}
          </p>
        </div>

        {activeTab === "bank" && (
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={
                  allVisibleSelected
                }
                onChange={
                  toggleAllVisibleVariants
                }
                disabled={
                  loading ||
                  variants.length === 0
                }
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />

              Выбрать страницу
            </label>

            <button
              type="button"
              onClick={() => {
                void handleExportVariants();
              }}
              disabled={
                exporting ||
                selectedVariantIds.size ===
                  0
              }
              className="btn-primary"
            >
              {exporting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Формирование ZIP...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />

                  Экспорт ZIP (
                  {
                    selectedVariantIds.size
                  }
                  )
                </>
              )}
            </button>
          </div>
        )}
      </div>


      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : variants.length === 0 ? (
        <section className="card py-12 text-center">
          {activeTab === "queue" ? (
            <CheckCircle2 className="mx-auto h-12 w-12 text-green-400" />
          ) : (
            <Package className="mx-auto h-12 w-12 text-gray-300" />
          )}

          <h3 className="mt-4 text-lg font-semibold text-gray-900">
            {activeTab === "queue"
              ? "Очередь пуста"
              : "Банк пока пуст"}
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            {activeTab === "queue"
              ? "Нет утверждённых вариантов, ожидающих публикации."
              : "Опубликованные варианты появятся здесь."}
          </p>
        </section>
      ) : (
        <div className="space-y-4">
          {variants.map((variant) => {
            const isExpanded =
              expandedVariantId ===
              variant.id;

            const isSelected =
              selectedVariantIds.has(
                variant.id
              );

            const questions =
              questionsByVariant[
                variant.id
              ] ?? [];

            const questionsLoading =
              loadingVariantId ===
              variant.id;

            const publishing =
              publishingVariantId ===
              variant.id;

            return (
              <article
                key={variant.id}
                className={`card overflow-hidden ${
                  isSelected
                    ? "ring-2 ring-primary-200"
                    : ""
                }`}
              >
                {activeTab === "bank" && (
                  <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
                    <input
                      type="checkbox"
                      checked={
                        isSelected
                      }
                      onChange={() => {
                        toggleVariantSelection(
                          variant.id
                        );
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      aria-label={
                        `Выбрать вариант ${variant.title}`
                      }
                    />

                    <button
                      type="button"
                      onClick={() => {
                        toggleVariantSelection(
                          variant.id
                        );
                      }}
                      className="text-sm font-medium text-gray-700 hover:text-primary-700"
                    >
                      Выбрать для экспорта
                    </button>
                  </div>
                )}

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
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs text-gray-400">
                        Вариант #{variant.id}
                      </span>

                      <span
                        className={
                          variant.status ===
                          "IN_BANK"
                            ? "badge bg-purple-100 text-purple-800"
                            : "badge bg-green-100 text-green-800"
                        }
                      >
                        {variant.status ===
                        "IN_BANK"
                          ? "В банке"
                          : "Утверждён"}
                      </span>
                    </div>

                    <h3 className="mt-2 text-lg font-semibold text-gray-900">
                      {variant.title}
                    </h3>

                    {variant.description && (
                      <p className="mt-1 line-clamp-2 text-sm text-gray-600">
                        {
                          variant.description
                        }
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
                        {
                          variant.question_count
                        }
                      </span>

                      <span>
                        Разработчик:{" "}
                        {
                          variant.developer_name
                        }
                      </span>

                      {variant.approved_at && (
                        <span>
                          Утверждён:{" "}
                          {format(
                            new Date(
                              variant.approved_at
                            ),
                            "d MMM yyyy, HH:mm",
                            {
                              locale: ru,
                            }
                          )}
                        </span>
                      )}

                      {variant.published_at && (
                        <span>
                          Опубликован:{" "}
                          {format(
                            new Date(
                              variant.published_at
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
                    {variant.review_comment && (
                      <div className="mb-6 rounded-xl border border-green-200 bg-green-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-green-700">
                          Рецензия верификатора
                        </p>

                        <p className="mt-2 whitespace-pre-wrap text-sm text-green-900">
                          {
                            variant.review_comment
                          }
                        </p>

                        {variant.reviewer_name && (
                          <p className="mt-2 text-xs text-green-700">
                            Верификатор:{" "}
                            {
                              variant.reviewer_name
                            }
                          </p>
                        )}
                      </div>
                    )}


                    {questionsLoading ? (
                      <div className="flex h-40 items-center justify-center">
                        <div className="h-7 w-7 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
                      </div>
                    ) : questions.length ===
                      0 ? (
                      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                        В варианте не найдены вопросы.
                      </div>
                    ) : (
                      <div className="space-y-6">
                        {questions.map(
                          (question) => (
                            <CuratorQuestionCard
                              key={
                                question.id
                              }
                              question={
                                question
                              }
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


                    {activeTab ===
                      "queue" && (
                      <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-5">
                        <div className="mb-3 flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-gray-500" />

                          <h4 className="text-sm font-semibold text-gray-800">
                            Комментарий к публикации
                          </h4>
                        </div>

                        <textarea
                          value={
                            curatorComment
                          }
                          onChange={(
                            event
                          ) => {
                            setCuratorComment(
                              event.target
                                .value
                            );
                          }}
                          className="input-field min-h-32 resize-y"
                          placeholder="Укажите комментарий к добавлению варианта в банк..."
                          minLength={1}
                          maxLength={5000}
                          disabled={
                            publishing
                          }
                          required
                        />

                        <p className="mt-1 text-right text-xs text-gray-400">
                          {
                            curatorComment.length
                          }{" "}
                          / 5000
                        </p>

                        <button
                          type="button"
                          onClick={() => {
                            void handlePublish(
                              variant
                            );
                          }}
                          disabled={
                            publishing ||
                            questionsLoading ||
                            questions.length ===
                              0 ||
                            !curatorComment.trim()
                          }
                          className="btn-primary mt-4"
                        >
                          <Send className="h-4 w-4" />

                          {publishing
                            ? "Публикация..."
                            : "Добавить вариант в банк"}
                        </button>

                        <p className="mt-3 text-xs text-gray-500">
                          В банк будет добавлен
                          весь вариант со всеми
                          вопросами, формулами и
                          изображениями.
                        </p>
                      </div>
                    )}


                    {activeTab ===
                      "bank" &&
                      variant.curator_comment && (
                        <div className="mt-6 rounded-xl border border-purple-200 bg-purple-50 p-4">
                          <p className="text-xs font-semibold uppercase tracking-wide text-purple-700">
                            Комментарий куратора
                          </p>

                          <p className="mt-2 whitespace-pre-wrap text-sm text-purple-900">
                            {
                              variant.curator_comment
                            }
                          </p>
                        </div>
                      )}
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
              changePage(
                Math.max(
                  1,
                  page - 1
                )
              );
            }}
            disabled={page === 1}
            className="btn-secondary"
          >
            Назад
          </button>

          <span className="text-sm text-gray-500">
            Страница {page} из{" "}
            {totalPages}
          </span>

          <button
            type="button"
            onClick={() => {
              changePage(
                Math.min(
                  totalPages,
                  page + 1
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


function CuratorQuestionCard({
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
            <h4 className="font-semibold text-gray-900">
              Вопрос №
              {question.order_number}
            </h4>

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
          <h5 className="mb-3 text-sm font-semibold text-gray-800">
            Ресурсный блок
          </h5>

          <div className="grid gap-4 xl:grid-cols-2">
            <MarkdownBlock
              label="Қазақша"
              value={
                question.resource_kz
              }
            />

            <MarkdownBlock
              label="Русский"
              value={
                question.resource_ru
              }
            />
          </div>
        </div>
      )}


      <div className="mt-5">
        <h5 className="mb-3 text-sm font-semibold text-gray-800">
          Текст вопроса
        </h5>

        <div className="grid gap-4 xl:grid-cols-2">
          <MarkdownBlock
            label="Қазақша"
            value={
              question.question_text_kz
            }
          />

          <MarkdownBlock
            label="Русский"
            value={
              question.question_text_ru
            }
          />
        </div>
      </div>


      <div className="mt-5">
        <h5 className="mb-3 text-sm font-semibold text-gray-800">
          Варианты ответа
        </h5>

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
                    value={
                      option.text_kz
                    }
                    compact
                  />

                  <MarkdownBlock
                    label="RU"
                    value={
                      option.text_ru
                    }
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
          <h5 className="mb-3 text-sm font-semibold text-gray-800">
            Пояснение к ответу
          </h5>

          <div className="grid gap-4 xl:grid-cols-2">
            <MarkdownBlock
              label="Қазақша"
              value={
                question.explanation_kz
              }
            />

            <MarkdownBlock
              label="Русский"
              value={
                question.explanation_ru
              }
            />
          </div>
        </div>
      )}


      {question.media_files.length >
        0 && (
        <div className="mt-5">
          <h5 className="mb-3 text-sm font-semibold text-gray-800">
            Изображения
          </h5>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {question.media_files.map(
              (media) => (
                <a
                  key={media.id}
                  href={
                    media.public_url
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="overflow-hidden rounded-xl border border-gray-200 bg-gray-50 hover:border-primary-300"
                >
                  <div className="flex h-44 items-center justify-center p-3">
                    <img
                      src={
                        media.public_url
                      }
                      alt={
                        media.original_filename
                      }
                      className="max-h-full max-w-full object-contain"
                      loading="lazy"
                    />
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