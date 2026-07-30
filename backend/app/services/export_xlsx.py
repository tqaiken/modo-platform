"""Generate registry.xlsx from questions."""
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


def generate_registry_xlsx(questions: list) -> bytes:
    """Create an Excel registry with question data."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Реестр вопросов"

    # ── Styles ──
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    wrap = Alignment(wrap_text=True, vertical="top")

    # ── Headers ──
    headers = [
        "ID", "Предмет", "Тема", "Текст вопроса",
        "Вариант A", "Вариант B", "Вариант C", "Вариант D",
        "Правильный ответ", "Сложность", "Автор", "Статус",
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # ── Data rows ──
    for row_idx, q in enumerate(questions, 2):
        options = q.options or []
        correct_letters = []
        for i, opt in enumerate(options):
            if opt.get("is_correct"):
                correct_letters.append(chr(65 + i))  # A, B, C, D...

        row_data = [
            q.id,
            q.subject or "",
            q.topic or "",
            q.body,
            options[0].get("text", "") if len(options) > 0 else "",
            options[1].get("text", "") if len(options) > 1 else "",
            options[2].get("text", "") if len(options) > 2 else "",
            options[3].get("text", "") if len(options) > 3 else "",
            ", ".join(correct_letters),
            q.difficulty,
            q.author.full_name if q.author else "",
            q.status.value,
        ]
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.alignment = wrap

    # ── Column widths ──
    widths = [8, 15, 20, 50, 30, 30, 30, 30, 15, 10, 20, 15]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else "A"].width = w

    # Save to bytes
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
