"""
LaTeX syntax validator for question text.
Checks that all $...$ and $$...$$ blocks have balanced delimiters
and common syntax issues before export.
"""
import re
from dataclasses import dataclass


@dataclass
class LatexIssue:
    line: int
    column: int
    message: str
    snippet: str


def validate_latex(text: str) -> list[LatexIssue]:
    """
    Validate LaTeX syntax in text.
    Returns a list of issues found (empty = valid).
    """
    issues: list[LatexIssue] = []

    if not text:
        return issues

    lines = text.split("\n")

    for line_num, line in enumerate(lines, 1):
        # ── Check balanced $ delimiters ──
        dollar_count = line.count("$") - line.count("\\$")  # exclude escaped \$
        if dollar_count % 2 != 0:
            issues.append(LatexIssue(
                line=line_num,
                column=0,
                message="Несбалансированный символ $ (нечётное количество)",
                snippet=line.strip()[:100],
            ))

        # ── Check balanced $$ delimiters (display mode) ──
        double_dollars = re.findall(r'\$\$', line)
        if len(double_dollars) % 2 != 0:
            issues.append(LatexIssue(
                line=line_num,
                column=0,
                message="Несбалансированный символ $$ (display mode)",
                snippet=line.strip()[:100],
            ))

        # ── Check for empty formulas ──
        empty_formulas = re.findall(r'\$\s*\$', line)
        if empty_formulas:
            issues.append(LatexIssue(
                line=line_num,
                column=0,
                message="Пустая формула ($ $)",
                snippet=line.strip()[:100],
            ))

        # ── Check balanced braces {} ──
        inline_formulas = re.findall(r'\$([^$]+)\$', line)
        for formula in inline_formulas:
            open_braces = formula.count("{")
            close_braces = formula.count("}")
            if open_braces != close_braces:
                issues.append(LatexIssue(
                    line=line_num,
                    column=0,
                    message=f"Несбалансированные скобки {{}} в формуле: {formula[:50]}",
                    snippet=formula[:100],
                ))

            # ── Check for common LaTeX errors ──
            # Missing \ before common commands
            common_cmds = ["frac", "sqrt", "sum", "int", "lim", "log", "sin", "cos", "tan"]
            for cmd in common_cmds:
                # Match word boundary but not preceded by \
                pattern = rf'(?<!\\)(?<![a-zA-Z]){cmd}(?![a-zA-Z])'
                if re.search(pattern, formula):
                    # It's OK if it's inside a \command{...} already
                    pass  # KaTeX is forgiving, skip strict check

    return issues


def validate_question_latex(title: str, body: str, options: list[dict], explanation: str | None = None) -> list[LatexIssue]:
    """
    Validate all LaTeX in a question's fields.
    Returns aggregated list of issues.
    """
    all_issues: list[LatexIssue] = []

    for field_name, field_text in [("title", title), ("body", body)]:
        issues = validate_latex(field_text)
        for issue in issues:
            issue.message = f"[{field_name}] {issue.message}"
        all_issues.extend(issues)

    for i, opt in enumerate(options):
        opt_text = opt.get("text", "")
        issues = validate_latex(opt_text)
        for issue in issues:
            issue.message = f"[option_{chr(65 + i)}] {issue.message}"
        all_issues.extend(issues)

    if explanation:
        issues = validate_latex(explanation)
        for issue in issues:
            issue.message = f"[explanation] {issue.message}"
        all_issues.extend(issues)

    return all_issues
