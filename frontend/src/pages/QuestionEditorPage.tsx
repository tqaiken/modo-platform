import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, uploadMedia, deleteMedia } from "../services/api";
import { renderLatex } from "../utils/latex";
import {
  Save,
  Send,
  Plus,
  Trash2,
  Upload,
  X,
  Eye,
  EyeOff,
  CheckCircle2,
  Image as ImageIcon,
} from "lucide-react";
import toast from "react-hot-toast";

interface Option {
  text: string;
  is_correct: boolean;
}

interface MediaFile {
  id: number;
  public_url: string;
  original_filename: string;
  content_type: string;
  file_size: number;
}

export default function QuestionEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [options, setOptions] = useState<Option[]>([
    { text: "", is_correct: false },
    { text: "", is_correct: false },
  ]);
  const [explanation, setExplanation] = useState("");
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState(1);
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [questionId, setQuestionId] = useState<number | null>(null);

  // Load existing question
  useEffect(() => {
    if (isEditing) {
      api.get(`/api/v1/questions/${id}`).then((res) => {
        const q = res.data;
        setTitle(q.title);
        setBody(q.body);
        setOptions(q.options);
        setExplanation(q.explanation || "");
        setSubject(q.subject || "");
        setTopic(q.topic || "");
        setDifficulty(q.difficulty);
        setMediaFiles(q.media_files || []);
        setQuestionId(q.id);
      });
    }
  }, [id, isEditing]);

  // ── Options management ──
  const addOption = () => {
    if (options.length >= 10) return;
    setOptions([...options, { text: "", is_correct: false }]);
  };

  const removeOption = (index: number) => {
    if (options.length <= 2) return;
    setOptions(options.filter((_, i) => i !== index));
  };

  const updateOption = (index: number, field: keyof Option, value: any) => {
    const updated = [...options];
    updated[index] = { ...updated[index], [field]: value };
    setOptions(updated);
  };

  const setCorrectOption = (index: number) => {
    const updated = options.map((opt, i) => ({
      ...opt,
      is_correct: i === index,
    }));
    setOptions(updated);
  };

  // ── Save (create or update) ──
  const handleSave = useCallback(async () => {
    if (!title.trim() || !body.trim()) {
      toast.error("Заполните название и текст вопроса");
      return;
    }
    if (options.some((o) => !o.text.trim())) {
      toast.error("Заполните все варианты ответов");
      return;
    }
    if (!options.some((o) => o.is_correct)) {
      toast.error("Выберите правильный ответ");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        title,
        body,
        options,
        explanation: explanation || null,
        subject: subject || null,
        topic: topic || null,
        difficulty,
      };

      let res;
      if (isEditing && questionId) {
        res = await api.put(`/api/v1/questions/${questionId}`, payload);
      } else {
        res = await api.post("/api/v1/questions", payload);
        setQuestionId(res.data.id);
      }

      toast.success(isEditing ? "Вопрос обновлён" : "Вопрос создан");
      if (!isEditing) {
        navigate(`/questions/${res.data.id}/edit`, { replace: true });
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }, [
    title,
    body,
    options,
    explanation,
    subject,
    topic,
    difficulty,
    isEditing,
    questionId,
    navigate,
  ]);

  // ── Submit for verification ──
  const handleSubmit = async () => {
    if (!questionId) {
      toast.error("Сначала сохраните вопрос");
      return;
    }

    try {
      await api.post(`/api/v1/questions/${questionId}/submit`);
      toast.success("Вопрос отправлен на верификацию");
      navigate("/developer");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Ошибка отправки");
    }
  };

  // ── Media upload ──
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!questionId) {
      toast.error("Сначала сохраните вопрос");
      return;
    }

    setUploading(true);
    try {
      const result = await uploadMedia(questionId, file);
      setMediaFiles((prev) => [...prev, result as MediaFile]);
      toast.success("Файл загружен");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteMedia = async (mediaId: number) => {
    try {
      await deleteMedia(mediaId);
      setMediaFiles((prev) => prev.filter((m) => m.id !== mediaId));
      toast.success("Файл удалён");
    } catch {
      toast.error("Ошибка удаления");
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? "Редактирование вопроса" : "Новый вопрос"}
        </h1>
        <div className="flex gap-3">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="btn-secondary"
          >
            {showPreview ? (
              <>
                <EyeOff className="h-4 w-4" /> Редактор
              </>
            ) : (
              <>
                <Eye className="h-4 w-4" /> Превью
              </>
            )}
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            <Save className="h-4 w-4" />
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
          {questionId && (
            <button onClick={handleSubmit} className="btn-primary bg-amber-600 hover:bg-amber-700">
              <Send className="h-4 w-4" />
              На верификацию
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {/* Title */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Название вопроса
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input-field"
            placeholder="Краткое описание вопроса"
          />
        </div>

        {/* Subject / Topic / Difficulty */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Предмет
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="input-field"
              placeholder="Математика"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Тема
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="input-field"
              placeholder="Алгебра"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Сложность (1-5)
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(Number(e.target.value))}
              className="input-field"
            >
              {[1, 2, 3, 4, 5].map((d) => (
                <option key={d} value={d}>
                  {"★".repeat(d)}
                  {"☆".repeat(5 - d)} ({d})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Body editor / preview */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Текст вопроса{" "}
            <span className="text-gray-400">(поддержка LaTeX: $E = mc^2$)</span>
          </label>
          {showPreview ? (
            <div
              className="card min-h-[120px] prose max-w-none"
              dangerouslySetInnerHTML={{ __html: renderLatex(body) }}
            />
          ) : (
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="input-field min-h-[120px] resize-y font-mono text-sm"
              placeholder="Введите текст вопроса. Используйте $...$ для формул."
            />
          )}
        </div>

        {/* Options */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Варианты ответов
            </label>
            <button onClick={addOption} className="btn-secondary text-xs" disabled={options.length >= 10}>
              <Plus className="h-3 w-3" /> Добавить вариант
            </button>
          </div>

          <div className="space-y-3">
            {options.map((opt, i) => (
              <div key={i} className="flex items-start gap-3">
                <button
                  onClick={() => setCorrectOption(i)}
                  className={`mt-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors ${
                    opt.is_correct
                      ? "border-green-500 bg-green-500 text-white"
                      : "border-gray-300 text-gray-400 hover:border-green-300"
                  }`}
                >
                  {opt.is_correct ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    String.fromCharCode(65 + i)
                  )}
                </button>

                <div className="flex-1">
                  {showPreview ? (
                    <div
                      className="card py-2 text-sm"
                      dangerouslySetInnerHTML={{ __html: renderLatex(opt.text) }}
                    />
                  ) : (
                    <input
                      type="text"
                      value={opt.text}
                      onChange={(e) => updateOption(i, "text", e.target.value)}
                      className="input-field"
                      placeholder={`Вариант ${String.fromCharCode(65 + i)}`}
                    />
                  )}
                </div>

                <button
                  onClick={() => removeOption(i)}
                  disabled={options.length <= 2}
                  className="mt-2 text-gray-400 hover:text-red-500 disabled:opacity-30"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Explanation */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Пояснение к ответу
          </label>
          {showPreview ? (
            <div
              className="card min-h-[60px] prose max-w-none"
              dangerouslySetInnerHTML={{
                __html: renderLatex(explanation),
              }}
            />
          ) : (
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              className="input-field min-h-[80px] resize-y font-mono text-sm"
              placeholder="Объяснение правильного ответа"
            />
          )}
        </div>

        {/* Media upload */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Изображения (схемы, карты, графики)
          </label>
          <p className="mb-3 text-xs text-gray-500">
            Загружаются в оригинальном качестве без сжатия
          </p>

          <div className="mb-4">
            <label className="btn-secondary cursor-pointer">
              <Upload className="h-4 w-4" />
              {uploading ? "Загрузка..." : "Загрузить файл"}
              <input
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>
          </div>

          {mediaFiles.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {mediaFiles.map((m) => (
                <div key={m.id} className="group relative">
                  <img
                    src={m.public_url}
                    alt={m.original_filename}
                    className="h-40 w-full rounded-lg border border-gray-200 object-contain bg-gray-50"
                  />
                  <div className="mt-1 flex items-center justify-between">
                    <span className="truncate text-xs text-gray-500">
                      {m.original_filename}
                    </span>
                    <button
                      onClick={() => handleDeleteMedia(m.id)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
