import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../services/api";
import { renderLatex } from "../utils/latex";
import { getStatusBadge, QuestionStatus } from "../utils/status";
import { ArrowLeft, CheckCircle2, Clock, User } from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface Question {
  id: number;
  title: string;
  body: string;
  body_html: string | null;
  options: { text: string; is_correct: boolean }[];
  explanation: string | null;
  subject: string | null;
  topic: string | null;
  difficulty: number;
  status: QuestionStatus;
  author: { id: number; full_name: string; email: string };
  reviewer: { id: number; full_name: string; email: string } | null;
  media_files: { id: number; public_url: string; original_filename: string }[];
  comments: { id: number; content: string; author: { full_name: string }; created_at: string }[];
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}

export default function QuestionViewPage() {
  const { id } = useParams();
  const [question, setQuestion] = useState<Question | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      api
        .get(`/api/v1/questions/${id}`)
        .then((res) => setQuestion(res.data))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!question) {
    return (
      <div className="card py-12 text-center">
        <p className="text-gray-500">Вопрос не найден</p>
      </div>
    );
  }

  const statusCfg = getStatusBadge(question.status);

  return (
    <div className="mx-auto max-w-3xl">
      {/* Back link */}
      <Link
        to="/developer"
        className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Назад к списку
      </Link>

      {/* Header */}
      <div className="mb-6">
        <div className="mb-2 flex items-center gap-3">
          <span className="text-xs text-gray-400">#{question.id}</span>
          <span className={statusCfg.class}>{statusCfg.label}</span>
          <span className="text-xs text-gray-400">
            {"★".repeat(question.difficulty)}
            {"☆".repeat(5 - question.difficulty)}
          </span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{question.title}</h1>
        <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
          {question.subject && <span>📚 {question.subject}</span>}
          {question.topic && <span>📁 {question.topic}</span>}
          <span className="flex items-center gap-1">
            <User className="h-3.5 w-3.5" />
            {question.author.full_name}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {format(new Date(question.created_at), "d MMM yyyy, HH:mm", {
              locale: ru,
            })}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="card mb-6">
        <div
          className="prose max-w-none text-gray-700"
          dangerouslySetInnerHTML={{ __html: renderLatex(question.body) }}
        />
      </div>

      {/* Options */}
      <div className="card mb-6">
        <h2 className="mb-4 text-sm font-medium text-gray-700">Варианты ответов</h2>
        <div className="space-y-3">
          {question.options.map((opt, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 rounded-lg p-4 ${
                opt.is_correct
                  ? "border border-green-200 bg-green-50"
                  : "bg-gray-50"
              }`}
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-200 text-sm font-bold">
                {String.fromCharCode(65 + i)}
              </span>
              <div
                className="flex-1 text-sm"
                dangerouslySetInnerHTML={{ __html: renderLatex(opt.text) }}
              />
              {opt.is_correct && (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Explanation */}
      {question.explanation && (
        <div className="card mb-6">
          <h2 className="mb-3 text-sm font-medium text-gray-700">Пояснение</h2>
          <div
            className="text-sm text-gray-600"
            dangerouslySetInnerHTML={{ __html: renderLatex(question.explanation) }}
          />
        </div>
      )}

      {/* Media */}
      {question.media_files.length > 0 && (
        <div className="card mb-6">
          <h2 className="mb-4 text-sm font-medium text-gray-700">
            Изображения ({question.media_files.length})
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {question.media_files.map((m) => (
              <a
                key={m.id}
                href={m.public_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img
                  src={m.public_url}
                  alt={m.original_filename}
                  className="h-48 w-full rounded-lg border border-gray-200 object-contain bg-gray-50"
                />
                <p className="mt-1 truncate text-xs text-gray-500">
                  {m.original_filename}
                </p>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Comments */}
      {question.comments.length > 0 && (
        <div className="card mb-6">
          <h2 className="mb-4 text-sm font-medium text-gray-700">
            Комментарии ({question.comments.length})
          </h2>
          <div className="space-y-4">
            {question.comments.map((c) => (
              <div key={c.id} className="rounded-lg bg-gray-50 p-4">
                <div className="mb-2 flex items-center gap-2 text-xs text-gray-500">
                  <User className="h-3.5 w-3.5" />
                  <span className="font-medium text-gray-700">
                    {c.author.full_name}
                  </span>
                  <span>
                    {format(new Date(c.created_at), "d MMM yyyy, HH:mm", {
                      locale: ru,
                    })}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{c.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="card">
        <h2 className="mb-4 text-sm font-medium text-gray-700">Хронология</h2>
        <div className="space-y-3 text-sm text-gray-500">
          <div>
            📝 Создан:{" "}
            {format(new Date(question.created_at), "d MMM yyyy, HH:mm", {
              locale: ru,
            })}
          </div>
          {question.submitted_at && (
            <div>
              📤 Отправлен на проверку:{" "}
              {format(new Date(question.submitted_at), "d MMM yyyy, HH:mm", {
                locale: ru,
              })}
            </div>
          )}
          {question.reviewed_at && (
            <div>
              🔍 Проверен:{" "}
              {format(new Date(question.reviewed_at), "d MMM yyyy, HH:mm", {
                locale: ru,
              })}
              {question.reviewer && ` — ${question.reviewer.full_name}`}
            </div>
          )}
          {question.approved_at && (
            <div>
              ✅ Утверждён:{" "}
              {format(new Date(question.approved_at), "d MMM yyyy, HH:mm", {
                locale: ru,
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
