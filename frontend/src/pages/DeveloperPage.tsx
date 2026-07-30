import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { getStatusBadge, QuestionStatus } from "../utils/status";
import { Plus, Search, Filter } from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface Question {
  id: number;
  title: string;
  status: QuestionStatus;
  subject: string | null;
  topic: string | null;
  difficulty: number;
  created_at: string;
  updated_at: string;
}

export default function DeveloperPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<QuestionStatus | "">("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuestions();
  }, [page, statusFilter]);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 20 };
      if (statusFilter) params.status = statusFilter;
      const res = await api.get("/api/v1/questions/my", { params });
      setQuestions(res.data.items);
      setTotal(res.data.total);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Мои вопросы</h1>
          <p className="text-sm text-gray-500">
            Всего: {total} вопрос(ов)
          </p>
        </div>
        <Link to="/questions/new" className="btn-primary">
          <Plus className="h-4 w-4" />
          Новый вопрос
        </Link>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as QuestionStatus | "");
            setPage(1);
          }}
          className="input-field w-48"
        >
          <option value="">Все статусы</option>
          <option value="DRAFT">Черновик</option>
          <option value="VERIFICATION">На проверке</option>
          <option value="REVISION">Доработка</option>
          <option value="IN_BANK">В банке</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : questions.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">Вопросов пока нет</p>
          <Link to="/questions/new" className="btn-primary mt-4">
            <Plus className="h-4 w-4" />
            Создать первый вопрос
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Название
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Предмет
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Статус
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Обновлен
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {questions.map((q) => {
                const statusCfg = getStatusBadge(q.status);
                return (
                  <tr key={q.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      #{q.id}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      <Link
                        to={`/questions/${q.id}`}
                        className="hover:text-primary-600"
                      >
                        {q.title}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {q.subject || "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className={statusCfg.class}>
                        {statusCfg.label}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {format(new Date(q.updated_at), "d MMM yyyy, HH:mm", {
                        locale: ru,
                      })}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm">
                      {(q.status === "DRAFT" || q.status === "REVISION") && (
                        <Link
                          to={`/questions/${q.id}/edit`}
                          className="font-medium text-primary-600 hover:text-primary-500"
                        >
                          Редактировать
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary"
          >
            Назад
          </button>
          <span className="text-sm text-gray-500">
            Страница {page} из {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            className="btn-secondary"
          >
            Вперёд
          </button>
        </div>
      )}
    </div>
  );
}
