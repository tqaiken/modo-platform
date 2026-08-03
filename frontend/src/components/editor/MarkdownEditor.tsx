import {
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Bold,
  Code2,
  Eye,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Pencil,
  Quote,
  Sigma,
  Table2,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import FormulaEditorModal from "./FormulaEditorModal";

import "katex/dist/katex.min.css";


type EditorMode =
  | "edit"
  | "preview";


type MarkdownEditorProps = {
  id?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  minHeightClassName?: string;
  maxLength?: number;
  helpText?: string;
};


type ToolbarAction = {
  label: string;
  title: string;
  icon: ReactNode;
  execute: () => void;
};


export default function MarkdownEditor({
  id,
  label,
  value,
  onChange,
  placeholder,
  required = false,
  minHeightClassName = "min-h-40",
  maxLength = 50000,
  helpText,
}: MarkdownEditorProps) {
  const textareaRef =
    useRef<HTMLTextAreaElement | null>(null);

  const [mode, setMode] =
    useState<EditorMode>("edit");

  const [formulaModalOpen, setFormulaModalOpen] =
    useState(false);

  const [selectedFormula, setSelectedFormula] =
    useState("");


  const replaceSelection = (
    replacement: string,
    selectionOffset = replacement.length
  ): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      onChange(value + replacement);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    const nextValue =
      value.slice(0, start) +
      replacement +
      value.slice(end);

    onChange(nextValue);

    const nextCursor =
      start + selectionOffset;

    window.setTimeout(() => {
      textarea.focus();

      textarea.setSelectionRange(
        nextCursor,
        nextCursor
      );
    }, 0);
  };


  const wrapSelection = (
    prefix: string,
    suffix: string,
    fallback: string
  ): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      replaceSelection(
        `${prefix}${fallback}${suffix}`
      );

      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    const selectedText =
      value.slice(start, end) || fallback;

    const replacement =
      `${prefix}${selectedText}${suffix}`;

    const nextValue =
      value.slice(0, start) +
      replacement +
      value.slice(end);

    onChange(nextValue);

    window.setTimeout(() => {
      textarea.focus();

      if (start === end) {
        textarea.setSelectionRange(
          start + prefix.length,
          start + prefix.length +
            selectedText.length
        );
      } else {
        textarea.setSelectionRange(
          start,
          start + replacement.length
        );
      }
    }, 0);
  };


  const prefixSelectedLines = (
    prefix: string
  ): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      replaceSelection(prefix);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    const selectedText =
      value.slice(start, end) || "Элемент";

    const replacement = selectedText
      .split("\n")
      .map((line) => `${prefix}${line}`)
      .join("\n");

    const nextValue =
      value.slice(0, start) +
      replacement +
      value.slice(end);

    onChange(nextValue);

    window.setTimeout(() => {
      textarea.focus();

      textarea.setSelectionRange(
        start,
        start + replacement.length
      );
    }, 0);
  };


  const prefixNumberedLines = (): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      replaceSelection("1. Элемент");
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    const selectedText =
      value.slice(start, end) || "Элемент";

    const replacement = selectedText
      .split("\n")
      .map(
        (line, index) =>
          `${index + 1}. ${line}`
      )
      .join("\n");

    const nextValue =
      value.slice(0, start) +
      replacement +
      value.slice(end);

    onChange(nextValue);

    window.setTimeout(() => {
      textarea.focus();

      textarea.setSelectionRange(
        start,
        start + replacement.length
      );
    }, 0);
  };


  const openFormulaEditor = (): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      setSelectedFormula("");
      setFormulaModalOpen(true);
      return;
    }

    const selectedText = value.slice(
      textarea.selectionStart,
      textarea.selectionEnd
    );

    setSelectedFormula(selectedText);
    setFormulaModalOpen(true);
  };


  const insertFormula = (
    markdown: string
  ): void => {
    replaceSelection(markdown);
  };


  const toolbarActions: ToolbarAction[] = [
    {
      label: "B",
      title: "Жирный",
      icon: <Bold className="h-4 w-4" />,
      execute: () => {
        wrapSelection(
          "**",
          "**",
          "жирный текст"
        );
      },
    },
    {
      label: "I",
      title: "Курсив",
      icon: <Italic className="h-4 w-4" />,
      execute: () => {
        wrapSelection(
          "_",
          "_",
          "курсив"
        );
      },
    },
    {
      label: "Код",
      title: "Фрагмент кода",
      icon: <Code2 className="h-4 w-4" />,
      execute: () => {
        wrapSelection(
          "`",
          "`",
          "код"
        );
      },
    },
    {
      label: "Список",
      title: "Маркированный список",
      icon: <List className="h-4 w-4" />,
      execute: () => {
        prefixSelectedLines("- ");
      },
    },
    {
      label: "Нумерация",
      title: "Нумерованный список",
      icon: (
        <ListOrdered className="h-4 w-4" />
      ),
      execute: prefixNumberedLines,
    },
    {
      label: "Цитата",
      title: "Цитата",
      icon: <Quote className="h-4 w-4" />,
      execute: () => {
        prefixSelectedLines("> ");
      },
    },
    {
      label: "Ссылка",
      title: "Ссылка",
      icon: (
        <LinkIcon className="h-4 w-4" />
      ),
      execute: () => {
        wrapSelection(
          "[",
          "](https://example.com)",
          "текст ссылки"
        );
      },
    },
    {
      label: "Таблица",
      title: "Таблица",
      icon: <Table2 className="h-4 w-4" />,
      execute: () => {
        replaceSelection(
          "\n\n| Колонка 1 | Колонка 2 |\n" +
            "| --- | --- |\n" +
            "| Значение 1 | Значение 2 |\n\n"
        );
      },
    },
  ];


  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
        <label
          htmlFor={id}
          className="block text-sm font-medium text-gray-700"
        >
          {label}

          {required && (
            <span className="ml-1 text-red-500">
              *
            </span>
          )}
        </label>

        <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-1">
          <button
            type="button"
            onClick={() => {
              setMode("edit");
            }}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${
              mode === "edit"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-gray-600"
            }`}
          >
            <Pencil className="h-3.5 w-3.5" />
            Редактор
          </button>

          <button
            type="button"
            onClick={() => {
              setMode("preview");
            }}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${
              mode === "preview"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-gray-600"
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            Предпросмотр
          </button>
        </div>
      </div>


      {mode === "edit" ? (
        <div className="overflow-hidden rounded-lg border border-gray-300 bg-white focus-within:border-primary-500 focus-within:ring-1 focus-within:ring-primary-500">
          <div className="flex flex-wrap items-center gap-1 border-b border-gray-200 bg-gray-50 p-2">
            {toolbarActions.map((action) => (
              <button
                key={action.title}
                type="button"
                onClick={action.execute}
                title={action.title}
                className="inline-flex h-8 min-w-8 items-center justify-center gap-1 rounded-md px-2 text-xs font-medium text-gray-600 hover:bg-white hover:text-primary-700 hover:shadow-sm"
              >
                {action.icon}
                <span className="sr-only">
                  {action.label}
                </span>
              </button>
            ))}

            <div className="mx-1 h-5 w-px bg-gray-300" />

            <button
              type="button"
              onClick={openFormulaEditor}
              title="Вставить формулу"
              className="inline-flex h-8 items-center gap-2 rounded-md bg-primary-50 px-3 text-xs font-medium text-primary-700 hover:bg-primary-100"
            >
              <Sigma className="h-4 w-4" />
              Формула
            </button>
          </div>

          <textarea
            ref={textareaRef}
            id={id}
            value={value}
            onChange={(event) => {
              onChange(event.target.value);
            }}
            className={`w-full resize-y border-0 px-3 py-3 font-mono text-sm text-gray-900 outline-none ${minHeightClassName}`}
            placeholder={placeholder}
            required={required}
            maxLength={maxLength}
          />
        </div>
      ) : (
        <div
          className={`prose max-w-none overflow-auto rounded-lg border border-gray-200 bg-white p-4 ${minHeightClassName}`}
        >
          {value.trim() ? (
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
          ) : (
            <p className="text-sm text-gray-400">
              Нет содержимого для предварительного просмотра
            </p>
          )}
        </div>
      )}


      <div className="mt-1.5 flex items-start justify-between gap-3">
        <p className="text-xs text-gray-500">
          {helpText ??
            "Поддерживаются Markdown и формулы LaTeX."}
        </p>

        <p className="shrink-0 text-xs text-gray-400">
          {value.length} / {maxLength}
        </p>
      </div>


      <FormulaEditorModal
        isOpen={formulaModalOpen}
        initialLatex={selectedFormula}
        onClose={() => {
          setFormulaModalOpen(false);
          setSelectedFormula("");
        }}
        onInsert={insertFormula}
      />
    </div>
  );
}