import katex from "katex";

/**
 * Render inline LaTeX formulas ($...$) in text to HTML.
 * Non-formula text is returned as-is (escaped).
 */
export function renderLatex(text: string): string {
  if (!text) return "";

  // Escape HTML entities in non-LaTeX parts
  const escapeHtml = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  // Split by $...$ patterns
  const parts = text.split(/(\$[^$]+\$)/g);

  return parts
    .map((part) => {
      if (part.startsWith("$") && part.endsWith("$")) {
        const formula = part.slice(1, -1);
        try {
          return katex.renderToString(formula, {
            throwOnError: false,
            displayMode: false,
          });
        } catch {
          return `<span class="text-red-500">${escapeHtml(formula)}</span>`;
        }
      }
      return escapeHtml(part);
    })
    .join("");
}

/**
 * Render block LaTeX ($$...$$) as display mode.
 */
export function renderLatexBlock(text: string): string {
  if (!text) return "";

  const escapeHtml = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const parts = text.split(/(\$\$[^$]+\$\$)/g);

  return parts
    .map((part) => {
      if (part.startsWith("$$") && part.endsWith("$$")) {
        const formula = part.slice(2, -2);
        try {
          return katex.renderToString(formula, {
            throwOnError: false,
            displayMode: true,
          });
        } catch {
          return `<div class="text-red-500">${escapeHtml(formula)}</div>`;
        }
      }
      // Also handle inline $...$
      return renderLatex(part);
    })
    .join("");
}
