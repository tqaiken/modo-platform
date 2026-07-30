import { useState, useEffect } from "react";
import { api } from "../services/api";
import { renderLatex } from "../utils/latex";
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface Question {
  id: number;
  title: string;
  body: string;
  options: { text: string; is_correct: boolean }[];
  explanation: string | null;
  subject: string | null;
  topic: string | null;
  difficulty: number;
  author: { id: number; full_name: string; email: string };
  media_files: { id: number; public_url: string; original_filename: string }[];
  submitted_at: string | null;
}

export default function VerifierPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchQueue();
  }, [page]);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/v1/questions/verification-queue", {
        params: { page, page_size: 20 },
      });
      setQuestions(res.data.items);
      setTotal(res.data.total);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (questionId: number, approved: boolean) => {
    if (!reviewComment.trim()) {
      toast.error("Добавьте комментарий к проверке");
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/api/v1/questions/${questionId}/review`, {
        approved,
        comment: reviewComment,
      });
      toast.success(
        approved ? "Вопрос одобрен и добавлен в банк" : "Вопрос возвращён на доработку"
      );
      setReviewComment("");
      setExpandedId(null);
      fetchQueue();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Ошибка при проверке");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Очередь проверки</h1>
        <p className="text-sm text-gray-500">
          {total} вопрос(ов) ожидают проверки
        </p>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : questions.length === 0 ? (
        <div className="card py-12 text-center">
          <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-400" />
          <p className="text-gray-500">Очередь пуста — все вопросы проверены</p>
        </div>
      ) : (
        <div className="space-y-4">
          {questions.map((q) => {
            const isExpanded = expandedId === q.id;

            return (
              <div key={q.id} className="card">
                {/* Header row */}
                <div
                  className="flex cursor-pointer items-start justify-between"
                  onClick={() => {
                    setExpandedId(isExpanded ? null : q.id);
                    setReviewComment("");
                  }}
                >
                  <div className="flex-1">
                    <div className="mb-1 flex items-center gap-3">
                      <span className="text-xs text-gray-400">#{q.id}</span>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {q.title}
                      </h3>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      {q.subject && <span>📚 {q.subject}</span>}
                      {q.topic && <span>📁 {q.topic}</span>}
                      <span>
                        Сложность: {"★".repeat(q.difficulty)}
                        {"☆".repeat(5 - q.difficulty)}
                      </span>
                      <span>Автор: {q.author.full_name}</span>
                      {q.submitted_at && (
                        <span>
                          Отправлен:{" "}
                          {format(new Date(q.submitted_at), "d MMM yyyy, HH:mm", {
                            locale: ru,
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  )}
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="mt-6 border-t border-gray-100 pt-6">
                    {/* Question body */}
                    <div
                      className="mb-4 text-gray-700"
                      dangerouslySetInnerHTML={{ __html: renderLatex(q.body) }}
                    />

                    {/* Options */}
                    <div className="mb-4 space-y-2">
                      {q.options.map((opt, i) => (
                        <div
                          key={i}
                          className={`flex items-start gap-3 rounded-lg p-3 ${
                            opt.is_correct
                              ? "border border-green-200 bg-green-50"
                              : "bg-gray-50"
                          }`}
                        >
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-medium">
                            {String.fromCharCode(65 + i)}
                          </span>
                          <span
                            className="text-sm"
                            dangerouslySetInnerHTML={{
                              __html: renderLatex(opt.text),
                            }}
                          />
                          {opt.is_correct && (
                            <CheckCircle2 className="ml-auto h-5 w-5 text-green-500" />
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Explanation */}
                    {q.explanation && (
                      <div className="mb-4 rounded-lg bg-blue-50 p-4">
                        <p className="mb-1 text-xs font-medium text-blue-700">
                          Пояснение:
                        </p>
                        <div
                          className="text-sm text-blue-900"
                          dangerouslySetInnerHTML={{
                            __html: renderLatex(q.explanation),
                          }}
                        />
                      </div>
                    )}

                    {/* Media files */}
                    {q.media_files.length > 0 && (
                      <div className="mb-4">
                        <p className="mb-2 text-xs font-medium text-gray-500">
                          Прикреплённые файлы:
                        </p>
                        <div className="flex flex-wrap gap-3">
                          {q.media_files.map((m) => (
                            <a
                              key={m.id}
                              href={m.public_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block"
                            >
                              <img
                                src={m.public_url}
                                alt={m.original_filename}
                                className="h-32 rounded-lg border border-gray-200 object-contain"
                              />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Review form */}
                    <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <div className="mb-3 flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-700">
                          Рецензия
                        </span>
                      </div>
                      <textarea
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        className="input-field mb-4 min-h-[100px] resize-y"
                        placeholder="Укажите замечания или комментарий к вопросу..."
                        required
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleReview(q.id, true)}
                          disabled={submitting}
                          className="btn-primary bg-green-600 hover:bg-green-700"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Одобрить
                        </button>
                        <button
                          onClick={() => handleReview(q.id, false)}
                          disabled={submitting}
                          className="btn-danger"
                        >
                          <XCircle className="h-4 w-4" />
                          На доработку
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
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
