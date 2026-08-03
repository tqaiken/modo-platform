import {
  useEffect,
  useRef,
  useState,
  type MouseEvent,
} from "react";
import {
  Braces,
  Check,
  X,
} from "lucide-react";
import katex from "katex";

import "katex/dist/katex.min.css";


type FormulaMode =
  | "inline"
  | "block";


type FormulaTemplate = {
  label: string;
  value: string;
  title: string;
};


type FormulaEditorModalProps = {
  isOpen: boolean;
  initialLatex?: string;
  onClose: () => void;
  onInsert: (markdown: string) => void;
};


const BASIC_SYMBOLS: FormulaTemplate[] = [
  {
    label: "+",
    value: "+",
    title: "Сложение",
  },
  {
    label: "−",
    value: "-",
    title: "Вычитание",
  },
  {
    label: "×",
    value: "\\times",
    title: "Умножение",
  },
  {
    label: "÷",
    value: "\\div",
    title: "Деление",
  },
  {
    label: "=",
    value: "=",
    title: "Равно",
  },
  {
    label: "≠",
    value: "\\ne",
    title: "Не равно",
  },
  {
    label: "<",
    value: "<",
    title: "Меньше",
  },
  {
    label: ">",
    value: ">",
    title: "Больше",
  },
  {
    label: "≤",
    value: "\\le",
    title: "Меньше или равно",
  },
  {
    label: "≥",
    value: "\\ge",
    title: "Больше или равно",
  },
  {
    label: "±",
    value: "\\pm",
    title: "Плюс-минус",
  },
  {
    label: "∞",
    value: "\\infty",
    title: "Бесконечность",
  },
];


const GREEK_SYMBOLS: FormulaTemplate[] = [
  {
    label: "π",
    value: "\\pi",
    title: "Пи",
  },
  {
    label: "α",
    value: "\\alpha",
    title: "Альфа",
  },
  {
    label: "β",
    value: "\\beta",
    title: "Бета",
  },
  {
    label: "γ",
    value: "\\gamma",
    title: "Гамма",
  },
  {
    label: "δ",
    value: "\\delta",
    title: "Дельта",
  },
  {
    label: "θ",
    value: "\\theta",
    title: "Тета",
  },
  {
    label: "λ",
    value: "\\lambda",
    title: "Лямбда",
  },
  {
    label: "μ",
    value: "\\mu",
    title: "Мю",
  },
  {
    label: "σ",
    value: "\\sigma",
    title: "Сигма",
  },
  {
    label: "φ",
    value: "\\varphi",
    title: "Фи",
  },
  {
    label: "Ω",
    value: "\\Omega",
    title: "Омега",
  },
];


const SET_SYMBOLS: FormulaTemplate[] = [
  {
    label: "∈",
    value: "\\in",
    title: "Принадлежит",
  },
  {
    label: "∉",
    value: "\\notin",
    title: "Не принадлежит",
  },
  {
    label: "⊂",
    value: "\\subset",
    title: "Подмножество",
  },
  {
    label: "⊆",
    value: "\\subseteq",
    title: "Подмножество или равно",
  },
  {
    label: "∪",
    value: "\\cup",
    title: "Объединение",
  },
  {
    label: "∩",
    value: "\\cap",
    title: "Пересечение",
  },
  {
    label: "∅",
    value: "\\varnothing",
    title: "Пустое множество",
  },
  {
    label: "ℕ",
    value: "\\mathbb{N}",
    title: "Натуральные числа",
  },
  {
    label: "ℤ",
    value: "\\mathbb{Z}",
    title: "Целые числа",
  },
  {
    label: "ℚ",
    value: "\\mathbb{Q}",
    title: "Рациональные числа",
  },
  {
    label: "ℝ",
    value: "\\mathbb{R}",
    title: "Действительные числа",
  },
];


const FORMULA_TEMPLATES: FormulaTemplate[] = [
  {
    label: "Дробь",
    value: "\\frac{a}{b}",
    title: "Обыкновенная дробь",
  },
  {
    label: "Корень",
    value: "\\sqrt{x}",
    title: "Квадратный корень",
  },
  {
    label: "Корень n",
    value: "\\sqrt[n]{x}",
    title: "Корень произвольной степени",
  },
  {
    label: "Степень",
    value: "x^{n}",
    title: "Степень",
  },
  {
    label: "Индекс",
    value: "x_{n}",
    title: "Нижний индекс",
  },
  {
    label: "Сумма",
    value: "\\sum_{i=1}^{n} x_i",
    title: "Сумма",
  },
  {
    label: "Интеграл",
    value: "\\int_{a}^{b} f(x)\\,dx",
    title: "Определённый интеграл",
  },
  {
    label: "Предел",
    value: "\\lim_{x \\to a} f(x)",
    title: "Предел функции",
  },
  {
    label: "Логарифм",
    value: "\\log_{a}{x}",
    title: "Логарифм",
  },
  {
    label: "Модуль",
    value: "\\left|x\\right|",
    title: "Модуль",
  },
  {
    label: "Скобки",
    value: "\\left(x\\right)",
    title: "Масштабируемые круглые скобки",
  },
  {
    label: "Система",
    value:
      "\\begin{cases}\nx+y=1 \\\\\nx-y=0\n\\end{cases}",
    title: "Система уравнений",
  },
  {
    label: "Матрица",
    value:
      "\\begin{pmatrix}\na & b \\\\\nc & d\n\\end{pmatrix}",
    title: "Матрица",
  },
];


function cleanInitialLatex(
  value: string
): string {
  const trimmed = value.trim();

  if (
    trimmed.startsWith("$$") &&
    trimmed.endsWith("$$")
  ) {
    return trimmed.slice(2, -2).trim();
  }

  if (
    trimmed.startsWith("$") &&
    trimmed.endsWith("$")
  ) {
    return trimmed.slice(1, -1).trim();
  }

  return trimmed;
}


export default function FormulaEditorModal({
  isOpen,
  initialLatex = "",
  onClose,
  onInsert,
}: FormulaEditorModalProps) {
  const textareaRef =
    useRef<HTMLTextAreaElement | null>(null);

  const [latex, setLatex] = useState("");
  const [mode, setMode] =
    useState<FormulaMode>("inline");


  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const cleaned =
      cleanInitialLatex(initialLatex);

    setLatex(cleaned);

    if (
      initialLatex.trim().startsWith("$$")
    ) {
      setMode("block");
    } else {
      setMode("inline");
    }

    window.setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  }, [initialLatex, isOpen]);


  if (!isOpen) {
    return null;
  }


  const insertAtCursor = (
    value: string
  ): void => {
    const textarea = textareaRef.current;

    if (!textarea) {
      setLatex((current) =>
        current
          ? `${current} ${value}`
          : value
      );

      return;
    }

    const selectionStart =
      textarea.selectionStart;

    const selectionEnd =
      textarea.selectionEnd;

    const before = latex.slice(
      0,
      selectionStart
    );

    const after = latex.slice(
      selectionEnd
    );

    const needsLeadingSpace =
      before.length > 0 &&
      !before.endsWith(" ") &&
      !before.endsWith("\n");

    const insertion =
      `${needsLeadingSpace ? " " : ""}${value}`;

    const nextValue =
      before + insertion + after;

    const nextCursorPosition =
      before.length + insertion.length;

    setLatex(nextValue);

    window.setTimeout(() => {
      textarea.focus();

      textarea.setSelectionRange(
        nextCursorPosition,
        nextCursorPosition
      );
    }, 0);
  };


  const renderedFormula = (() => {
    if (!latex.trim()) {
      return "";
    }

    try {
      return katex.renderToString(
        latex,
        {
          displayMode: mode === "block",
          throwOnError: false,
          strict: "warn",
          output: "html",
        }
      );
    } catch {
      return "";
    }
  })();


  const handleBackdropClick = (
    event: MouseEvent<HTMLDivElement>
  ): void => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };


  const handleInsert = (): void => {
    const normalizedLatex =
      latex.trim();

    if (!normalizedLatex) {
      return;
    }

    const markdown =
      mode === "inline"
        ? `$${normalizedLatex}$`
        : `\n\n$$\n${normalizedLatex}\n$$\n\n`;

    onInsert(markdown);
    onClose();
  };


  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 p-4"
      onMouseDown={handleBackdropClick}
    >
      <div
        className="flex max-h-[95vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="formula-editor-title"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-100 text-primary-700">
              <Braces className="h-5 w-5" />
            </div>

            <div>
              <h2
                id="formula-editor-title"
                className="text-lg font-semibold text-gray-900"
              >
                Редактор формул
              </h2>

              <p className="text-sm text-gray-500">
                Формула сохраняется в исходном LaTeX
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900"
            aria-label="Закрыть редактор формул"
          >
            <X className="h-5 w-5" />
          </button>
        </div>


        <div className="overflow-y-auto">
          <div className="space-y-5 border-b border-gray-200 bg-gray-50 px-6 py-5">
            <SymbolSection
              title="Основные символы"
              items={BASIC_SYMBOLS}
              onInsert={insertAtCursor}
            />

            <SymbolSection
              title="Греческие буквы"
              items={GREEK_SYMBOLS}
              onInsert={insertAtCursor}
            />

            <SymbolSection
              title="Множества"
              items={SET_SYMBOLS}
              onInsert={insertAtCursor}
            />

            <SymbolSection
              title="Шаблоны"
              items={FORMULA_TEMPLATES}
              onInsert={insertAtCursor}
              wide
            />
          </div>


          <div className="grid gap-0 lg:grid-cols-2">
            <section className="border-b border-gray-200 p-6 lg:border-b-0 lg:border-r">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-semibold text-gray-900">
                  LaTeX
                </h3>

                <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-1">
                  <button
                    type="button"
                    onClick={() => {
                      setMode("inline");
                    }}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                      mode === "inline"
                        ? "bg-white text-primary-700 shadow-sm"
                        : "text-gray-600"
                    }`}
                  >
                    В строке
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setMode("block");
                    }}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                      mode === "block"
                        ? "bg-white text-primary-700 shadow-sm"
                        : "text-gray-600"
                    }`}
                  >
                    Отдельный блок
                  </button>
                </div>
              </div>

              <textarea
                ref={textareaRef}
                value={latex}
                onChange={(event) => {
                  setLatex(event.target.value);
                }}
                className="input-field min-h-72 resize-y font-mono text-sm"
                placeholder="\frac{x+1}{y}"
                spellCheck={false}
              />

              <p className="mt-2 text-xs text-gray-500">
                Можно вводить LaTeX вручную или использовать
                кнопки символов и шаблонов.
              </p>
            </section>


            <section className="p-6">
              <h3 className="mb-4 font-semibold text-gray-900">
                Предварительный просмотр
              </h3>

              <div className="flex min-h-72 items-center justify-center overflow-auto rounded-xl border border-gray-200 bg-white p-6">
                {renderedFormula ? (
                  <div
                    className="max-w-full text-center text-lg"
                    dangerouslySetInnerHTML={{
                      __html: renderedFormula,
                    }}
                  />
                ) : (
                  <p className="text-sm text-gray-400">
                    Введите формулу для предварительного просмотра
                  </p>
                )}
              </div>
            </section>
          </div>
        </div>


        <div className="flex flex-wrap justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
          >
            Отмена
          </button>

          <button
            type="button"
            onClick={handleInsert}
            disabled={!latex.trim()}
            className="btn-primary"
          >
            <Check className="h-4 w-4" />
            Вставить формулу
          </button>
        </div>
      </div>
    </div>
  );
}


function SymbolSection({
  title,
  items,
  onInsert,
  wide = false,
}: {
  title: string;
  items: FormulaTemplate[];
  onInsert: (value: string) => void;
  wide?: boolean;
}) {
  return (
    <section>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </h3>

      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <button
            key={`${item.title}-${item.value}`}
            type="button"
            onClick={() => {
              onInsert(item.value);
            }}
            title={item.title}
            className={
              wide
                ? "rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:border-primary-300 hover:text-primary-700"
                : "flex h-10 min-w-10 items-center justify-center rounded-lg border border-gray-200 bg-white px-2 text-base font-medium text-gray-700 shadow-sm hover:border-primary-300 hover:text-primary-700"
            }
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  );
}