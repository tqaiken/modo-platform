import {
  createElement,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ImagePlus,
  Plus,
  Save,
  Trash2,
  X,
} from "lucide-react";
import {
  Link,
  useNavigate,
  useParams,
} from "react-router-dom";
import toast from "react-hot-toast";

import MarkdownEditor from "../components/editor/MarkdownEditor";
import {
  api,
  deleteMedia,
  uploadMedia,
} from "../services/api";


type CognitiveLevel =
  | "BASIC"
  | "MEDIUM"
  | "HIGH";


type VariantStatus =
  | "DRAFT"
  | "VERIFICATION"
  | "REVISION"
  | "APPROVED"
  | "IN_BANK";


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


interface BilingualOption {
  key: string;
  text_kz: string;
  text_ru: string;
  is_correct: boolean;
}


interface MediaFile {
  id: number;
  question_id?: number;
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


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const INITIAL_OPTIONS: BilingualOption[] = [
  {
    key: "A",
    text_kz: "",
    text_ru: "",
    is_correct: true,
  },
  {
    key: "B",
    text_kz: "",
    text_ru: "",
    is_correct: false,
  },
  {
    key: "C",
    text_kz: "",
    text_ru: "",
    is_correct: false,
  },
  {
    key: "D",
    text_kz: "",
    text_ru: "",
    is_correct: false,
  },
];


const COGNITIVE_LEVELS: Array<{
  value: CognitiveLevel;
  label: string;
  description: string;
}> = [
  {
    value: "BASIC",
    label: "Базовый",
    description: "Знание, понимание",
  },
  {
    value: "MEDIUM",
    label: "Средний",
    description: "Применение, анализ",
  },
  {
    value: "HIGH",
    label: "Высокий",
    description: "Синтез, оценка",
  },
];


const EDITABLE_STATUSES: VariantStatus[] = [
  "DRAFT",
  "REVISION",
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

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}


function createOptionKey(
  index: number
): string {
  return String.fromCharCode(
    "A".charCodeAt(0) + index
  );
}


function createInitialOptions(): BilingualOption[] {
  return INITIAL_OPTIONS.map((option) => ({
    ...option,
  }));
}


export default function QuestionEditorPage() {
  const {
    variantId,
    questionId: routeQuestionId,
  } = useParams<{
    variantId: string;
    questionId?: string;
  }>();

  const navigate = useNavigate();

  const numericVariantId = Number(variantId);

  const numericQuestionId =
    routeQuestionId === undefined
      ? null
      : Number(routeQuestionId);

  const isEditing =
    numericQuestionId !== null;


  const [variant, setVariant] =
    useState<Variant | null>(null);

  const [subjectTitle, setSubjectTitle] =
    useState("Загрузка...");

  const [objectives, setObjectives] =
    useState<LearningObjective[]>([]);

  const [
    learningObjectiveId,
    setLearningObjectiveId,
  ] = useState("");

  const [
    cognitiveLevel,
    setCognitiveLevel,
  ] = useState<CognitiveLevel>("BASIC");

  const [resourceKz, setResourceKz] =
    useState("");

  const [resourceRu, setResourceRu] =
    useState("");

  const [
    questionTextKz,
    setQuestionTextKz,
  ] = useState("");

  const [
    questionTextRu,
    setQuestionTextRu,
  ] = useState("");

  const [
    explanationKz,
    setExplanationKz,
  ] = useState("");

  const [
    explanationRu,
    setExplanationRu,
  ] = useState("");

  const [options, setOptions] =
    useState<BilingualOption[]>(
      createInitialOptions()
    );

  const [
    savedQuestionId,
    setSavedQuestionId,
  ] = useState<number | null>(
    numericQuestionId
  );

  const [mediaFiles, setMediaFiles] =
    useState<MediaFile[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [uploading, setUploading] =
    useState(false);


  const loadData = useCallback(
    async (): Promise<void> => {
      if (
        !Number.isInteger(numericVariantId) ||
        numericVariantId < 1
      ) {
        setLoading(false);
        return;
      }

      if (
        numericQuestionId !== null &&
        (
          !Number.isInteger(numericQuestionId) ||
          numericQuestionId < 1
        )
      ) {
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const [
          variantResponse,
          subjectsResponse,
          objectivesResponse,
        ] = await Promise.all([
          api.get<Variant>(
            `/api/v1/variants/${numericVariantId}`
          ),
          api.get<Subject[]>(
            "/api/v1/subjects"
          ),
          api.get<LearningObjectiveList>(
            "/api/v1/learning-objectives"
          ),
        ]);

        const loadedVariant =
          variantResponse.data;

        setVariant(loadedVariant);

        const subject =
          subjectsResponse.data.find(
            (item) =>
              item.id ===
              loadedVariant.subject_id
          );

        setSubjectTitle(
          subject?.title ??
            (
              loadedVariant.subject_id === null
                ? "Предмет не назначен"
                : `Предмет #${loadedVariant.subject_id}`
            )
        );

        setObjectives(
          objectivesResponse.data.items.filter(
            (objective) =>
              objective.is_active &&
              objective.subject_id ===
                loadedVariant.subject_id
          )
        );

        if (numericQuestionId === null) {
          return;
        }

        const questionsResponse =
          await api.get<VariantQuestionList>(
            `/api/v1/variants/${numericVariantId}/questions`
          );

        const question =
          questionsResponse.data.items.find(
            (item) =>
              item.id === numericQuestionId
          );

        if (!question) {
          throw new Error(
            "Вопрос не найден в варианте."
          );
        }

        setSavedQuestionId(question.id);

        setLearningObjectiveId(
          question.learning_objective_id === null
            ? ""
            : String(
                question.learning_objective_id
              )
        );

        setCognitiveLevel(
          question.cognitive_level ?? "BASIC"
        );

        setResourceKz(
          question.resource_kz ?? ""
        );

        setResourceRu(
          question.resource_ru ?? ""
        );

        setQuestionTextKz(
          question.question_text_kz ?? ""
        );

        setQuestionTextRu(
          question.question_text_ru ?? ""
        );

        setExplanationKz(
          question.explanation_kz ?? ""
        );

        setExplanationRu(
          question.explanation_ru ?? ""
        );

        if (
          Array.isArray(question.options) &&
          question.options.length >= 4
        ) {
          setOptions(
            question.options.map(
              (option, index) => ({
                key:
                  option.key ||
                  createOptionKey(index),
                text_kz:
                  option.text_kz || "",
                text_ru:
                  option.text_ru || "",
                is_correct:
                  Boolean(
                    option.is_correct
                  ),
              })
            )
          );
        } else {
          setOptions(
            createInitialOptions()
          );
        }

        setMediaFiles(
          question.media_files ?? []
        );
      } catch (error: unknown) {
        toast.error(
          getErrorMessage(
            error,
            "Не удалось загрузить редактор вопроса."
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [
      numericQuestionId,
      numericVariantId,
    ]
  );


  useEffect(() => {
    void loadData();
  }, [loadData]);


  const editable =
    variant !== null &&
    EDITABLE_STATUSES.includes(
      variant.status
    );


  const correctOptionKey = useMemo(() => {
    const correctOption = options.find(
      (option) => option.is_correct
    );

    return correctOption?.key ?? "";
  }, [options]);


  const updateOptionText = (
    index: number,
    field: "text_kz" | "text_ru",
    newText: string
  ): void => {
    setOptions((currentOptions) =>
      currentOptions.map(
        (option, optionIndex) => {
          if (optionIndex !== index) {
            return option;
          }

          if (field === "text_kz") {
            return {
              ...option,
              text_kz: newText,
            };
          }

          return {
            ...option,
            text_ru: newText,
          };
        }
      )
    );
  };


  const setCorrectOption = (
    key: string
  ): void => {
    setOptions((current) =>
      current.map((option) => ({
        ...option,
        is_correct:
          option.key === key,
      }))
    );
  };


  const addOption = (): void => {
    if (options.length >= 10) {
      toast.error(
        "Можно добавить не более 10 вариантов ответа."
      );
      return;
    }

    setOptions((current) => [
      ...current,
      {
        key: createOptionKey(
          current.length
        ),
        text_kz: "",
        text_ru: "",
        is_correct: false,
      },
    ]);
  };


  const removeOption = (
    index: number
  ): void => {
    if (options.length <= 4) {
      toast.error(
        "Должно быть не менее четырёх вариантов ответа."
      );
      return;
    }

    setOptions((current) => {
      const removedOption =
        current[index];

      const remaining = current
        .filter(
          (_, optionIndex) =>
            optionIndex !== index
        )
        .map((option, optionIndex) => ({
          ...option,
          key:
            createOptionKey(optionIndex),
        }));

      if (
        removedOption?.is_correct &&
        remaining.length > 0
      ) {
        remaining[0] = {
          ...remaining[0],
          is_correct: true,
        };
      }

      return remaining;
    });
  };


  const validateForm = (): boolean => {
    if (!learningObjectiveId) {
      toast.error("Выберите ОРО.");
      return false;
    }

    if (!questionTextKz.trim()) {
      toast.error(
        "Заполните текст вопроса на казахском языке."
      );
      return false;
    }

    if (!questionTextRu.trim()) {
      toast.error(
        "Заполните текст вопроса на русском языке."
      );
      return false;
    }

    if (options.length < 4) {
      toast.error(
        "Должно быть не менее четырёх вариантов ответа."
      );
      return false;
    }

    const incompleteOption =
      options.find(
        (option) =>
          !option.text_kz.trim() ||
          !option.text_ru.trim()
      );

    if (incompleteOption) {
      toast.error(
        `Заполните вариант ${incompleteOption.key} на двух языках.`
      );
      return false;
    }

    const correctOptionsCount =
      options.filter(
        (option) => option.is_correct
      ).length;

    if (correctOptionsCount !== 1) {
      toast.error(
        "Выберите ровно один правильный ответ."
      );
      return false;
    }

    return true;
  };


  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (
      variant === null ||
      !editable ||
      !validateForm()
    ) {
      return;
    }

    setSaving(true);

    const payload = {
      learning_objective_id:
        Number(learningObjectiveId),

      cognitive_level:
        cognitiveLevel,

      resource_kz:
        resourceKz.trim() || null,

      resource_ru:
        resourceRu.trim() || null,

      question_text_kz:
        questionTextKz.trim(),

      question_text_ru:
        questionTextRu.trim(),

      options: options.map(
        (option) => ({
          key: option.key,
          text_kz:
            option.text_kz.trim(),
          text_ru:
            option.text_ru.trim(),
          is_correct:
            option.is_correct,
        })
      ),

      explanation_kz:
        explanationKz.trim() || null,

      explanation_ru:
        explanationRu.trim() || null,
    };

    try {
      if (savedQuestionId !== null) {
        await api.patch(
          `/api/v1/variants/${variant.id}/questions/${savedQuestionId}`,
          payload
        );

        toast.success(
          "Вопрос сохранён."
        );

        return;
      }

      const response =
        await api.post<VariantQuestion>(
          `/api/v1/variants/${variant.id}/questions`,
          payload
        );

      setSavedQuestionId(
        response.data.id
      );

      setMediaFiles(
        response.data.media_files ?? []
      );

      toast.success(
        "Вопрос создан. Теперь можно загрузить изображения."
      );

      navigate(
        `/variants/${variant.id}/questions/${response.data.id}/edit`,
        {
          replace: true,
        }
      );
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось сохранить вопрос."
        )
      );
    } finally {
      setSaving(false);
    }
  };


  const handleFileUpload = async (
    event: ChangeEvent<HTMLInputElement>
  ): Promise<void> => {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    if (savedQuestionId === null) {
      toast.error(
        "Сначала сохраните вопрос."
      );

      event.target.value = "";
      return;
    }

    if (!file.type.startsWith("image/")) {
      toast.error(
        "Можно загружать только изображения."
      );

      event.target.value = "";
      return;
    }

    setUploading(true);

    try {
      const uploaded =
        await uploadMedia(
          savedQuestionId,
          file
        );

      setMediaFiles((current) => [
        ...current,
        uploaded as MediaFile,
      ]);

      toast.success(
        "Изображение загружено."
      );
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось загрузить изображение."
        )
      );
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };


  const handleDeleteMedia = async (
    mediaId: number
  ): Promise<void> => {
    const confirmed = window.confirm(
      "Удалить изображение?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteMedia(mediaId);

      setMediaFiles((current) =>
        current.filter(
          (media) =>
            media.id !== mediaId
        )
      );

      toast.success(
        "Изображение удалено."
      );
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось удалить изображение."
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
    numericVariantId < 1 ||
    variant === null
  ) {
    return (
      <MessageCard
        title="Вариант не найден"
        variantId={numericVariantId}
      />
    );
  }


  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <Link
          to={`/variants/${variant.id}`}
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад к варианту
        </Link>
      </div>


      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEditing
              ? "Редактирование вопроса"
              : "Новый вопрос"}
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Вариант: {variant.title}
          </p>
        </div>

        {savedQuestionId !== null && (
          <span className="badge bg-green-100 text-green-800">
            Вопрос сохранён
          </span>
        )}
      </div>


      {!editable && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Этот вариант нельзя редактировать
          в текущем статусе.
        </div>
      )}


      <form
        onSubmit={handleSubmit}
        className="space-y-8"
      >
        <section className="card space-y-5">
          <h2 className="text-lg font-semibold text-gray-900">
            Основные параметры
          </h2>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Предмет
            </label>

            <div className="relative">
              <BookOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

              <input
                value={subjectTitle}
                className="input-field cursor-not-allowed bg-gray-50 pl-10 text-gray-600"
                disabled
                readOnly
              />
            </div>

            <p className="mt-1.5 text-xs text-gray-500">
              Предмет наследуется из варианта
              и не может быть изменён.
            </p>
          </div>


          <div>
            <label
              htmlFor="learning-objective"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              ОРО
              <span className="ml-1 text-red-500">
                *
              </span>
            </label>

            <select
              id="learning-objective"
              value={learningObjectiveId}
              onChange={(event) => {
                setLearningObjectiveId(
                  event.target.value
                );
              }}
              className="input-field"
              disabled={!editable}
              required
            >
              <option value="">
                Выберите ожидаемый результат обучения
              </option>

              {objectives.map(
                (objective) => (
                  <option
                    key={objective.id}
                    value={objective.id}
                  >
                    {objective.code}:{" "}
                    {objective.title_ru}
                  </option>
                )
              )}
            </select>

            {objectives.length === 0 && (
              <p className="mt-1.5 text-xs text-amber-700">
                Для предмета ещё не созданы активные ОРО.
                Обратитесь к супер-администратору.
              </p>
            )}
          </div>


          <div>
            <label
              htmlFor="cognitive-level"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Уровень когнитивных навыков
              <span className="ml-1 text-red-500">
                *
              </span>
            </label>

            <select
              id="cognitive-level"
              value={cognitiveLevel}
              onChange={(event) => {
                setCognitiveLevel(
                  event.target.value as
                    CognitiveLevel
                );
              }}
              className="input-field"
              disabled={!editable}
              required
            >
              {COGNITIVE_LEVELS.map(
                (level) => (
                  <option
                    key={level.value}
                    value={level.value}
                  >
                    {level.label} (
                    {level.description})
                  </option>
                )
              )}
            </select>
          </div>
        </section>


        <section className="card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Блок ресурсов
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              Текст, график, рисунок, таблица,
              схема и другие материалы
            </p>
          </div>

          <MarkdownEditor
            id="resource-kz"
            label="Ресурсный блок на казахском"
            value={resourceKz}
            onChange={setResourceKz}
            placeholder="Мәтін, кесте, сызба немесе басқа ресурс"
            helpText="Поле необязательно. Поддерживаются Markdown и LaTeX."
          />

          <MarkdownEditor
            id="resource-ru"
            label="Ресурсный блок на русском"
            value={resourceRu}
            onChange={setResourceRu}
            placeholder="Текст, таблица, схема или другой ресурс"
            helpText="Поле необязательно. Поддерживаются Markdown и LaTeX."
          />
        </section>


        <section className="card space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Текст вопроса
          </h2>

          <MarkdownEditor
            id="question-text-kz"
            label="Текст вопроса на казахском"
            value={questionTextKz}
            onChange={setQuestionTextKz}
            placeholder="Сұрақ мәтінін енгізіңіз"
            required
            minHeightClassName="min-h-48"
          />

          <MarkdownEditor
            id="question-text-ru"
            label="Текст вопроса на русском"
            value={questionTextRu}
            onChange={setQuestionTextRu}
            placeholder="Введите текст вопроса"
            required
            minHeightClassName="min-h-48"
          />
        </section>


        <section className="card space-y-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Варианты ответа
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Минимум четыре ответа.
                Выберите ровно один правильный.
              </p>
            </div>

            <button
              type="button"
              onClick={addOption}
              disabled={
                !editable ||
                options.length >= 10
              }
              className="btn-secondary"
            >
              <Plus className="h-4 w-4" />
              Добавить ответ
            </button>
          </div>


          <div className="space-y-5">
            {options.map(
              (option, index) => (
                <article
                  key={option.key}
                  className={`rounded-xl border p-5 ${
                    option.is_correct
                      ? "border-green-300 bg-green-50/40"
                      : "border-gray-200 bg-white"
                  }`}
                >
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          setCorrectOption(
                            option.key
                          );
                        }}
                        disabled={!editable}
                        className={`flex h-10 w-10 items-center justify-center rounded-full border-2 font-bold ${
                          option.is_correct
                            ? "border-green-500 bg-green-500 text-white"
                            : "border-gray-300 bg-white text-gray-600 hover:border-green-400"
                        }`}
                        title="Выбрать правильный ответ"
                      >
                        {option.is_correct ? (
                          <CheckCircle2 className="h-5 w-5" />
                        ) : (
                          option.key
                        )}
                      </button>

                      <div>
                        <h3 className="font-semibold text-gray-900">
                          Ответ {option.key}
                        </h3>

                        <p className="text-xs text-gray-500">
                          {option.is_correct
                            ? "Правильный ответ"
                            : "Неправильный ответ"}
                        </p>
                      </div>
                    </div>

                    {options.length > 4 && (
                      <button
                        type="button"
                        onClick={() => {
                          removeOption(index);
                        }}
                        disabled={!editable}
                        className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        Удалить
                      </button>
                    )}
                  </div>


                  <div className="grid gap-5 xl:grid-cols-2">
                    <MarkdownEditor
                      id={`option-${option.key}-kz`}
                      label={`Ответ ${option.key} на казахском`}
                      value={option.text_kz}
                      onChange={(value) => {
                        updateOptionText(
                          index,
                          "text_kz",
                          value
                        );
                      }}
                      placeholder="Жауап нұсқасы"
                      required
                      minHeightClassName="min-h-28"
                      maxLength={5000}
                    />

                    <MarkdownEditor
                      id={`option-${option.key}-ru`}
                      label={`Ответ ${option.key} на русском`}
                      value={option.text_ru}
                      onChange={(value) => {
                        updateOptionText(
                          index,
                          "text_ru",
                          value
                        );
                      }}
                      placeholder="Вариант ответа"
                      required
                      minHeightClassName="min-h-28"
                      maxLength={5000}
                    />
                  </div>
                </article>
              )
            )}
          </div>


          <div className="rounded-lg bg-gray-50 p-4">
            <label
              htmlFor="correct-option"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Правильный ответ
            </label>

            <select
              id="correct-option"
              value={correctOptionKey}
              onChange={(event) => {
                setCorrectOption(
                  event.target.value
                );
              }}
              className="input-field max-w-xs"
              disabled={!editable}
              required
            >
              {options.map((option) => (
                <option
                  key={option.key}
                  value={option.key}
                >
                  Вариант {option.key}
                </option>
              ))}
            </select>
          </div>
        </section>


        <section className="card space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Пояснение к ответу
          </h2>

          <MarkdownEditor
            id="explanation-kz"
            label="Пояснение на казахском"
            value={explanationKz}
            onChange={setExplanationKz}
            placeholder="Дұрыс жауаптың түсіндірмесі"
            helpText="Поле необязательно."
          />

          <MarkdownEditor
            id="explanation-ru"
            label="Пояснение на русском"
            value={explanationRu}
            onChange={setExplanationRu}
            placeholder="Объяснение правильного ответа"
            helpText="Поле необязательно."
          />
        </section>


        <section className="card space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Изображения
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              После первого сохранения вопроса
              можно загружать изображения в исходном качестве.
            </p>
          </div>


          <div>
            <label
              className={`btn-secondary cursor-pointer ${
                savedQuestionId === null ||
                uploading ||
                !editable
                  ? "pointer-events-none opacity-50"
                  : ""
              }`}
            >
              <ImagePlus className="h-4 w-4" />

              {uploading
                ? "Загрузка..."
                : "Загрузить изображение"}

              <input
                type="file"
                accept="image/*"
                onChange={(event) => {
                  void handleFileUpload(
                    event
                  );
                }}
                disabled={
                  savedQuestionId === null ||
                  uploading ||
                  !editable
                }
                className="hidden"
              />
            </label>

            {savedQuestionId === null && (
              <p className="mt-2 text-xs text-amber-700">
                Сначала сохраните вопрос.
              </p>
            )}
          </div>


          {mediaFiles.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {mediaFiles.map((media) => (
                <article
                  key={media.id}
                  className="overflow-hidden rounded-xl border border-gray-200 bg-white"
                >
                  <div className="flex h-52 items-center justify-center bg-gray-50 p-3">
                    {createElement("img", {
                      src: media.public_url,
                      alt: media.original_filename,
                      className:
                        "max-h-full max-w-full object-contain",
                    })}
                  </div>

                  <div className="flex items-center justify-between gap-3 border-t border-gray-200 p-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-700">
                        {media.original_filename}
                      </p>

                      <p className="text-xs text-gray-400">
                        {Math.ceil(
                          media.file_size / 1024
                        )}{" "}
                        КБ
                      </p>
                    </div>

                    {editable && (
                      <button
                        type="button"
                        onClick={() => {
                          void handleDeleteMedia(
                            media.id
                          );
                        }}
                        className="shrink-0 rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
                        aria-label="Удалить изображение"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>


        <section className="sticky bottom-4 z-20 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white/95 p-4 shadow-lg backdrop-blur">
          <p className="text-sm text-gray-500">
            Вопрос сохраняется внутри варианта.
            Весь вариант отправляется
            на верификацию отдельно.
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              to={`/variants/${variant.id}`}
              className="btn-secondary"
            >
              Отмена
            </Link>

            <button
              type="submit"
              disabled={
                saving ||
                !editable ||
                objectives.length === 0
              }
              className="btn-primary"
            >
              <Save className="h-4 w-4" />

              {saving
                ? "Сохранение..."
                : savedQuestionId === null
                  ? "Создать вопрос"
                  : "Сохранить изменения"}
            </button>
          </div>
        </section>
      </form>
    </div>
  );
}


function MessageCard({
  title,
  variantId,
}: {
  title: string;
  variantId: number;
}) {
  const returnPath =
    Number.isInteger(variantId) &&
    variantId > 0
      ? `/variants/${variantId}`
      : "/developer";

  return (
    <section className="card py-12 text-center">
      <h1 className="text-lg font-semibold text-gray-900">
        {title}
      </h1>

      <p className="mt-2 text-sm text-gray-500">
        Проверьте адрес страницы или вернитесь к вариантам.
      </p>

      <Link
        to={returnPath}
        className="btn-primary mt-5"
      >
        Вернуться
      </Link>
    </section>
  );
}