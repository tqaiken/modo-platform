import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { getStatusBadge, QuestionStatus } from "../utils/status";
import {
  Download,
  Search,
  Package,
  Check,
  Eye,
} from "lucide-react";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface Question {
  id: number;
  title: string;
  subject: string | null;
  topic: string | null;
  difficulty: number;
  status: QuestionStatus;
  author: { full_name: string };
  approved_at: string | null;
}

export default function CuratorPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [subject, setSubject] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchBank();
  }, [page, search, subject]);

  const fetchBank = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 20 };
      if (search) params.search = search;
      if (subject) params.subject = subject;
      const res = await api.get("/api/v1/questions/bank", { params });
      setQuestions(res.data.items);
      setTotal(res.data.total);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === questions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(questions.map((q) => q.id)));
    }
  };

  const handleExport = async () => {
    if (selected.size === 0) {
      toast.error("Выберите вопросы для выгрузки");
      return;
    }

    setExporting(true);
    try {
      const res = await api.post(
        "/api/v1/export/zip",
        { question_ids: Array.from(selected) },
        { responseType: "blob" }
      );

      // Download the ZIP
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `test_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Выгружено ${selected.size} вопрос(ов)`);
    } catch (err: any) {
      toast.error("Ошибка при экспорте");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Банк заданий</h1>
          <p className="text-sm text-gray-500">
            {total} утверждённых вопрос(ов)
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || selected.size === 0}
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
              Экспорт ZIP ({selected.size})
            </>
          )}
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="input-field pl-10"
            placeholder="Поиск по названию или тексту..."
          />
        </div>
        <input
          type="text"
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
            setPage(1);
          }}
          className="input-field w-48"
          placeholder="Предмет"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : questions.length === 0 ? (
        <div className="card py-12 text-center">
          <Package className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">Банк пуст</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-12 px-6 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size === questions.length && questions.length > 0}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
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
                  Автор
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Утверждён
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Просмотр
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {questions.map((q) => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selected.has(q.id)}
                      onChange={() => toggleSelect(q.id)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    #{q.id}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {q.title}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {q.subject || "—"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {q.author?.full_name || "—"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {q.approved_at
                      ? format(new Date(q.approved_at), "d MMM yyyy", { locale: ru })
                      : "—"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm">
                    <Link
                      to={`/questions/${q.id}`}
                      className="inline-flex items-center gap-1 font-medium text-primary-600 hover:text-primary-500"
                    >
                      <Eye className="h-4 w-4" />
                      Открыть
                    </Link>
                  </td>
                </tr>
              ))}
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
