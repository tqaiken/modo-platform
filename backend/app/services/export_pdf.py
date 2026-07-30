"""Generate test_bank.pdf from questions — renders LaTeX formulas."""
import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.units import cm


def _escape_reportlab(text: str) -> str:
    """Escape XML special chars for ReportLab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_latex_text(text: str) -> str:
    """
    Convert inline LaTeX ($...$) to a simple text representation.
    For PDF export, we wrap LaTeX in <i> tags as approximation.
    Full KaTeX rendering is only in the web UI.
    """
    def replace_latex(m):
        formula = m.group(1)
        # Simple formatting — italicize the formula
        return f"<i>{_escape_reportlab(formula)}</i>"

    # Match $...$ (non-greedy)
    result = re.sub(r'\$([^$]+)\$', replace_latex, text)
    return result


def generate_test_bank_pdf(questions: list) -> bytes:
    """Create a PDF document with all questions."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="QuestionBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="OptionText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=15,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="MetaInfo",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.grey,
    ))

    story = []

    # ── Title page ──
    story.append(Paragraph("Банк тестовых заданий", styles["Title"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(f"Количество вопросов: {len(questions)}", styles["Normal"]))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", color=colors.grey))
    story.append(PageBreak())

    # ── Questions ──
    for i, q in enumerate(questions, 1):
        # Question number and title
        title = _escape_reportlab(q.title)
        story.append(Paragraph(f"<b>Вопрос {i}. {title}</b>", styles["Heading3"]))

        # Subject/topic
        meta_parts = []
        if q.subject:
            meta_parts.append(f"Предмет: {_escape_reportlab(q.subject)}")
        if q.topic:
            meta_parts.append(f"Тема: {_escape_reportlab(q.topic)}")
        meta_parts.append(f"Сложность: {'★' * q.difficulty}{'☆' * (5 - q.difficulty)}")
        if meta_parts:
            story.append(Paragraph(" | ".join(meta_parts), styles["MetaInfo"]))
            story.append(Spacer(1, 3 * mm))

        # Question body (with LaTeX rendering)
        body_text = _render_latex_text(q.body)
        story.append(Paragraph(body_text, styles["QuestionBody"]))
        story.append(Spacer(1, 3 * mm))

        # Options
        options = q.options or []
        for j, opt in enumerate(options):
            letter = chr(65 + j)
            opt_text = _render_latex_text(opt.get("text", ""))
            prefix = "✓ " if opt.get("is_correct") else "   "
            story.append(
                Paragraph(f"{prefix}<b>{letter})</b> {opt_text}", styles["OptionText"])
            )

        # Explanation
        if q.explanation:
            story.append(Spacer(1, 3 * mm))
            explanation = _render_latex_text(q.explanation)
            story.append(
                Paragraph(f"<b>Пояснение:</b> {explanation}", styles["MetaInfo"])
            )

        # Separator
        story.append(Spacer(1, 5 * mm))
        story.append(HRFlowable(width="100%", color=colors.lightgrey))
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
