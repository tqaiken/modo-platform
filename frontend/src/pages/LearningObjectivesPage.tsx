import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  Pencil,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";
import toast from "react-hot-toast";

import { api } from "../services/api";


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


interface ObjectiveForm {
  subject_id: string;
  code: string;
  title_kz: string;
  title_ru: string;
}


interface EditObjectiveForm {
  code: string;
  title_kz: string;
  title_ru: string;
  is_active: boolean;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const INITIAL_FORM: ObjectiveForm = {
  subject_id: "",
  code: "",
  title_kz: "",
  title_ru: "",
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


export default function LearningObjectivesPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [objectives, setObjectives] =
    useState<LearningObjective[]>([]);

  const [form, setForm] =
    useState<ObjectiveForm>(INITIAL_FORM);

  const [selectedSubjectId, setSelectedSubjectId] =
    useState("");

  const [editingObjectiveId, setEditingObjectiveId] =
    useState<number | null>(null);

  const [editForm, setEditForm] =
    useState<EditObjectiveForm | null>(null);

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);


  const loadSubjects = async (): Promise<Subject[]> => {
    const response = await api.get<Subject[]>(
      "/api/v1/subjects"
    );

    setSubjects(response.data);

    return response.data;
  };


  const loadObjectives = async (
    subjectId?: string
  ): Promise<void> => {
    const params: {
      subject_id?: number;
      include_inactive: boolean;
    } = {
      include_inactive: true,
    };

    if (subjectId) {
      params.subject_id = Number(subjectId);
    }

    const response =
      await api.get<LearningObjectiveList>(
        "/api/v1/learning-objectives",
        {
          params,
        }
      );

    setObjectives(response.data.items);
  };


  const loadData = async (): Promise<void> => {
    setLoading(true);

    try {
      const loadedSubjects = await loadSubjects();

      let effectiveSubjectId = selectedSubjectId;

      if (
        !effectiveSubjectId &&
        loadedSubjects.length > 0
      ) {
        effectiveSubjectId = String(
          loadedSubjects[0].id
        );

        setSelectedSubjectId(effectiveSubjectId);

        setForm((current) => ({
          ...current,
          subject_id: effectiveSubjectId,
        }));
      }

      await loadObjectives(effectiveSubjectId);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось загрузить справочник ОРО."
        )
      );
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    void loadData();
  }, []);


  const filteredObjectives = useMemo(() => {
    if (!selectedSubjectId) {
      return objectives;
    }

    return objectives.filter(
      (objective) =>
        objective.subject_id ===
        Number(selectedSubjectId)
    );
  }, [objectives, selectedSubjectId]);


  const selectedSubject = subjects.find(
    (subject) =>
      subject.id === Number(selectedSubjectId)
  );


  const getSubjectTitle = (
    subjectId: number
  ): string => {
    const subject = subjects.find(
      (item) => item.id === subjectId
    );

    return subject?.title ?? `Предмет #${subjectId}`;
  };


  const handleSubjectFilterChange = async (
    subjectId: string
  ): Promise<void> => {
    setSelectedSubjectId(subjectId);

    setForm((current) => ({
      ...current,
      subject_id: subjectId,
    }));

    setEditingObjectiveId(null);
    setEditForm(null);
    setLoading(true);

    try {
      await loadObjectives(subjectId);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось загрузить ОРО."
        )
      );
    } finally {
      setLoading(false);
    }
  };


  const handleCreateObjective = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (!form.subject_id) {
      toast.error("Выберите предмет.");
      return;
    }

    setCreating(true);

    try {
      await api.post(
        "/api/v1/learning-objectives",
        {
          subject_id: Number(form.subject_id),
          code: form.code.trim(),
          title_kz: form.title_kz.trim(),
          title_ru: form.title_ru.trim(),
        }
      );

      toast.success("ОРО создан.");

      setForm({
        subject_id: form.subject_id,
        code: "",
        title_kz: "",
        title_ru: "",
      });

      await loadObjectives(form.subject_id);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось создать ОРО."
        )
      );
    } finally {
      setCreating(false);
    }
  };


  const beginEdit = (
    objective: LearningObjective
  ): void => {
    setEditingObjectiveId(objective.id);

    setEditForm({
      code: objective.code,
      title_kz: objective.title_kz,
      title_ru: objective.title_ru,
      is_active: objective.is_active,
    });
  };


  const cancelEdit = (): void => {
    setEditingObjectiveId(null);
    setEditForm(null);
  };


  const handleUpdateObjective = async (
    event: FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();

    if (
      editingObjectiveId === null ||
      editForm === null
    ) {
      return;
    }

    setSaving(true);

    try {
      await api.patch(
        `/api/v1/learning-objectives/${editingObjectiveId}`,
        {
          code: editForm.code.trim(),
          title_kz: editForm.title_kz.trim(),
          title_ru: editForm.title_ru.trim(),
          is_active: editForm.is_active,
        }
      );

      toast.success("ОРО обновлён.");
      cancelEdit();

      await loadObjectives(selectedSubjectId);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось обновить ОРО."
        )
      );
    } finally {
      setSaving(false);
    }
  };


  const handleDeactivate = async (
    objective: LearningObjective
  ): Promise<void> => {
    if (!objective.is_active) {
      return;
    }

    const confirmed = window.confirm(
      `Деактивировать ОРО ${objective.code}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(
        `/api/v1/learning-objectives/${objective.id}`
      );

      toast.success("ОРО деактивирован.");

      await loadObjectives(selectedSubjectId);
    } catch (error: unknown) {
      toast.error(
        getErrorMessage(
          error,
          "Не удалось деактивировать ОРО."
        )
      );
    }
  };


  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/admin"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад в панель управления
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Ожидаемые результаты обучения
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Управление справочником ОРО по предметам
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


      {subjects.length === 0 ? (
        <section className="card py-12 text-center">
          <BookOpen className="mx-auto h-12 w-12 text-gray-300" />

          <h2 className="mt-4 text-lg font-semibold text-gray-900">
            Сначала создайте предмет
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            ОРО обязательно относится к конкретному предмету.
          </p>

          <Link
            to="/admin"
            className="btn-primary mt-5"
          >
            Перейти к предметам
          </Link>
        </section>
      ) : (
        <>
          <section className="card">
            <label
              htmlFor="subject-filter"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Предмет
            </label>

            <select
              id="subject-filter"
              value={selectedSubjectId}
              onChange={(event) => {
                void handleSubjectFilterChange(
                  event.target.value
                );
              }}
              className="input-field max-w-md"
            >
              {subjects.map((subject) => (
                <option
                  key={subject.id}
                  value={subject.id}
                >
                  {subject.title}
                </option>
              ))}
            </select>
          </section>


          <section className="grid gap-6 xl:grid-cols-2">
            <div className="card">
              <div className="mb-5">
                <h2 className="text-lg font-semibold text-gray-900">
                  Новый ОРО
                </h2>

                <p className="text-sm text-gray-500">
                  Предмет:{" "}
                  {selectedSubject?.title ??
                    "Не выбран"}
                </p>
              </div>

              <form
                onSubmit={handleCreateObjective}
                className="space-y-4"
              >
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Код ОРО
                  </label>

                  <input
                    value={form.code}
                    onChange={(event) => {
                      setForm((current) => ({
                        ...current,
                        code: event.target.value,
                      }));
                    }}
                    className="input-field"
                    placeholder="8.1.1.1"
                    minLength={1}
                    maxLength={100}
                    required
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    ОРО на казахском
                  </label>

                  <textarea
                    value={form.title_kz}
                    onChange={(event) => {
                      setForm((current) => ({
                        ...current,
                        title_kz:
                          event.target.value,
                      }));
                    }}
                    className="input-field min-h-28 resize-y"
                    maxLength={5000}
                    required
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    ОРО на русском
                  </label>

                  <textarea
                    value={form.title_ru}
                    onChange={(event) => {
                      setForm((current) => ({
                        ...current,
                        title_ru:
                          event.target.value,
                      }));
                    }}
                    className="input-field min-h-28 resize-y"
                    maxLength={5000}
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={creating}
                  className="btn-primary w-full"
                >
                  <Plus className="h-4 w-4" />

                  {creating
                    ? "Создание..."
                    : "Создать ОРО"}
                </button>
              </form>
            </div>


            {editForm !== null ? (
              <div className="card border-2 border-primary-100">
                <div className="mb-5 flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      Редактирование ОРО
                    </h2>

                    <p className="text-sm text-gray-500">
                      ID: {editingObjectiveId}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="rounded-lg p-2 text-gray-500 hover:bg-gray-100"
                    aria-label="Закрыть"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <form
                  onSubmit={handleUpdateObjective}
                  className="space-y-4"
                >
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700">
                      Код ОРО
                    </label>

                    <input
                      value={editForm.code}
                      onChange={(event) => {
                        setEditForm((current) =>
                          current === null
                            ? null
                            : {
                                ...current,
                                code:
                                  event.target.value,
                              }
                        );
                      }}
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700">
                      ОРО на казахском
                    </label>

                    <textarea
                      value={editForm.title_kz}
                      onChange={(event) => {
                        setEditForm((current) =>
                          current === null
                            ? null
                            : {
                                ...current,
                                title_kz:
                                  event.target.value,
                              }
                        );
                      }}
                      className="input-field min-h-28 resize-y"
                      required
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700">
                      ОРО на русском
                    </label>

                    <textarea
                      value={editForm.title_ru}
                      onChange={(event) => {
                        setEditForm((current) =>
                          current === null
                            ? null
                            : {
                                ...current,
                                title_ru:
                                  event.target.value,
                              }
                        );
                      }}
                      className="input-field min-h-28 resize-y"
                      required
                    />
                  </div>

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
                                is_active:
                                  event.target.checked,
                              }
                        );
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600"
                    />

                    <span className="text-sm font-medium text-gray-700">
                      ОРО активен
                    </span>
                  </label>

                  <div className="flex gap-3">
                    <button
                      type="submit"
                      disabled={saving}
                      className="btn-primary"
                    >
                      {saving
                        ? "Сохранение..."
                        : "Сохранить"}
                    </button>

                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="btn-secondary"
                    >
                      Отмена
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              <div className="card flex min-h-64 items-center justify-center text-center">
                <div>
                  <Pencil className="mx-auto h-10 w-10 text-gray-300" />

                  <p className="mt-3 text-sm text-gray-500">
                    Выберите ОРО в списке для редактирования
                  </p>
                </div>
              </div>
            )}
          </section>


          <section className="card overflow-hidden p-0">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-gray-900">
                ОРО предмета
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Всего: {filteredObjectives.length}
              </p>
            </div>

            {loading ? (
              <div className="flex h-40 items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
              </div>
            ) : filteredObjectives.length === 0 ? (
              <div className="px-6 py-10 text-center text-sm text-gray-500">
                Для выбранного предмета ОРО ещё не созданы.
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredObjectives.map(
                  (objective) => (
                    <div
                      key={objective.id}
                      className="px-6 py-5"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-gray-900">
                              {objective.code}
                            </span>

                            <span
                              className={
                                objective.is_active
                                  ? "badge bg-green-100 text-green-800"
                                  : "badge bg-gray-100 text-gray-700"
                              }
                            >
                              {objective.is_active
                                ? "Активен"
                                : "Неактивен"}
                            </span>
                          </div>

                          <p className="mt-2 text-sm text-gray-700">
                            <strong>KZ:</strong>{" "}
                            {objective.title_kz}
                          </p>

                          <p className="mt-1 text-sm text-gray-700">
                            <strong>RU:</strong>{" "}
                            {objective.title_ru}
                          </p>

                          <p className="mt-2 text-xs text-gray-400">
                            {getSubjectTitle(
                              objective.subject_id
                            )}
                          </p>
                        </div>

                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              beginEdit(objective);
                            }}
                            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50"
                          >
                            <Pencil className="h-4 w-4" />
                            Изменить
                          </button>

                          {objective.is_active && (
                            <button
                              type="button"
                              onClick={() => {
                                void handleDeactivate(
                                  objective
                                );
                              }}
                              className="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                            >
                              Деактивировать
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}