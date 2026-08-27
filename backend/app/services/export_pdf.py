"""
PDF export services.

Supported exports:

1. generate_test_bank_pdf(questions)
   Legacy export of individual questions.

2. generate_variants_test_bank_pdf(variants)
   Export of complete bilingual variants.

The PDF embeds a Unicode TrueType font to support:
- Cyrillic;
- Kazakh characters;
- mathematical symbols;
- bilingual question content.
"""

import html
import io
import logging
import re
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import (
    TA_CENTER,
    TA_LEFT,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.r2 import (
    create_s3_client,
    get_r2_bucket_name,
    normalize_r2_key,
)


logger = logging.getLogger(__name__)


FONT_REGULAR_NAME = "MODOUnicode"
FONT_BOLD_NAME = "MODOUnicodeBold"


FONT_CANDIDATES = [
    (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ),
    (
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ),
    (
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        ),
    ),
    (
        Path(
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Regular.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Bold.ttf"
        ),
    ),
    (
        Path(
            "/usr/share/fonts/truetype/liberation/"
            "LiberationSans-Regular.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/liberation/"
            "LiberationSans-Bold.ttf"
        ),
    ),
]


def register_unicode_fonts() -> tuple[str, str]:
    """
    Регистрирует Unicode-шрифты.

    Windows:
        Arial или Calibri.

    Linux / Render:
        DejaVu Sans или Liberation Sans.
    """
    registered_fonts = set(
        pdfmetrics.getRegisteredFontNames()
    )

    if (
        FONT_REGULAR_NAME in registered_fonts
        and FONT_BOLD_NAME in registered_fonts
    ):
        return (
            FONT_REGULAR_NAME,
            FONT_BOLD_NAME,
        )

    for regular_path, bold_path in FONT_CANDIDATES:
        if not (
            regular_path.exists()
            and bold_path.exists()
        ):
            continue

        try:
            pdfmetrics.registerFont(
                TTFont(
                    FONT_REGULAR_NAME,
                    str(regular_path),
                )
            )

            pdfmetrics.registerFont(
                TTFont(
                    FONT_BOLD_NAME,
                    str(bold_path),
                )
            )

            pdfmetrics.registerFontFamily(
                FONT_REGULAR_NAME,
                normal=FONT_REGULAR_NAME,
                bold=FONT_BOLD_NAME,
                italic=FONT_REGULAR_NAME,
                boldItalic=FONT_BOLD_NAME,
            )

            logger.info(
                "PDF Unicode font registered: %s",
                regular_path,
            )

            return (
                FONT_REGULAR_NAME,
                FONT_BOLD_NAME,
            )

        except Exception:
            logger.exception(
                "Failed to register PDF font: %s",
                regular_path,
            )

    raise RuntimeError(
        "Unicode PDF font was not found. "
        "Install DejaVu Sans or Liberation Sans."
    )


def escape_reportlab(
    value: Any,
) -> str:
    """
    Экранирует текст для ReportLab Paragraph.
    """
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def strip_markdown(
    value: str | None,
) -> str:
    """
    Преобразует Markdown и простой HTML
    в читаемый обычный текст.

    LaTeX-маркеры сохраняются.
    """
    if not value:
        return ""

    text = str(value)

    text = re.sub(
        r"```(?:\w+)?\s*(.*?)```",
        r"\1",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"`([^`]+)`",
        r"\1",
        text,
    )

    text = re.sub(
        r"!\[([^\]]*)\]\([^)]+\)",
        r"[Изображение: \1]",
        text,
    )

    text = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        text,
    )

    text = re.sub(
        r"^\s{0,3}#{1,6}\s+",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"(\*\*|__)(.*?)\1",
        r"\2",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*",
        r"\1",
        text,
    )

    text = re.sub(
        r"(?<!_)_([^_\n]+)_",
        r"\1",
        text,
    )

    text = re.sub(
        r"^\s*[-*+]\s+",
        "• ",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\s*(\d+)\.\s+",
        r"\1. ",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</p\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</div\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<[^>]+>",
        "",
        text,
    )

    text = html.unescape(text)

    text = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def prepare_paragraph_text(
    value: str | None,
) -> str:
    """
    Подготавливает текст для Paragraph.
    """
    cleaned = strip_markdown(
        value
    )

    escaped = escape_reportlab(
        cleaned
    )

    return escaped.replace(
        "\n",
        "<br/>",
    )


def get_enum_value(
    value: Any,
) -> str:
    if value is None:
        return ""

    enum_value = getattr(
        value,
        "value",
        None,
    )

    if enum_value is not None:
        return str(enum_value)

    return str(value)


def get_user_name(
    user: Any,
) -> str:
    if user is None:
        return "Не указан"

    full_name = getattr(
        user,
        "full_name",
        None,
    )

    if full_name:
        return str(full_name)

    username = getattr(
        user,
        "username",
        None,
    )

    if username:
        return str(username)

    user_id = getattr(
        user,
        "id",
        None,
    )

    if user_id is not None:
        return f"Пользователь #{user_id}"

    return "Не указан"


def get_subject_title(
    variant: Any,
) -> str:
    subject = getattr(
        variant,
        "subject",
        None,
    )

    if subject is not None:
        title = getattr(
            subject,
            "title",
            None,
        )

        if title:
            return str(title)

    subject_id = getattr(
        variant,
        "subject_id",
        None,
    )

    if subject_id is not None:
        return f"Предмет #{subject_id}"

    return "Не указан"


def get_variant_class(
    variant: Any,
) -> str:
    """
    Возвращает класс, если такое поле
    присутствует в модели варианта.
    """
    for field_name in (
        "grade",
        "class_name",
        "school_class",
    ):
        value = getattr(
            variant,
            field_name,
            None,
        )

        if value:
            return str(value)

    return "Не указан"


def get_objective_label(
    question: Any,
) -> str:
    objective = getattr(
        question,
        "learning_objective",
        None,
    )

    if objective is not None:
        code = str(
            getattr(
                objective,
                "code",
                "",
            )
            or ""
        )

        title_ru = str(
            getattr(
                objective,
                "title_ru",
                "",
            )
            or ""
        )

        if code and title_ru:
            return f"{code}: {title_ru}"

        return code or title_ru or "Не указан"

    objective_id = getattr(
        question,
        "learning_objective_id",
        None,
    )

    if objective_id is not None:
        return f"ОРО #{objective_id}"

    return "Не указан"


def normalize_options(
    question: Any,
) -> list[dict[str, Any]]:
    """
    Нормализует старые и двуязычные ответы.
    """
    raw_options = getattr(
        question,
        "options",
        None,
    ) or []

    if not isinstance(
        raw_options,
        list,
    ):
        return []

    result: list[dict[str, Any]] = []

    for index, option in enumerate(
        raw_options,
    ):
        if not isinstance(
            option,
            dict,
        ):
            continue

        default_key = chr(
            65 + index
        )

        legacy_text = str(
            option.get(
                "text",
                "",
            )
            or ""
        )

        result.append(
            {
                "key": str(
                    option.get(
                        "key",
                        default_key,
                    )
                    or default_key
                ),
                "text_kz": str(
                    option.get(
                        "text_kz",
                        legacy_text,
                    )
                    or ""
                ),
                "text_ru": str(
                    option.get(
                        "text_ru",
                        legacy_text,
                    )
                    or ""
                ),
                "is_correct": (
                    option.get(
                        "is_correct"
                    )
                    is True
                ),
            }
        )

    return result


def create_styles(
    regular_font: str,
    bold_font: str,
) -> dict[str, ParagraphStyle]:
    base_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            name="MODO_Title",
            parent=base_styles["Title"],
            fontName=bold_font,
            fontSize=20,
            leading=25,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=8 * mm,
        ),
        "variant_title": ParagraphStyle(
            name="MODO_VariantTitle",
            parent=base_styles["Heading1"],
            fontName=bold_font,
            fontSize=16,
            leading=21,
            textColor=colors.HexColor(
                "#1D4ED8"
            ),
            spaceBefore=3 * mm,
            spaceAfter=4 * mm,
        ),
        "question_title": ParagraphStyle(
            name="MODO_QuestionTitle",
            parent=base_styles["Heading2"],
            fontName=bold_font,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
        ),
        "section": ParagraphStyle(
            name="MODO_Section",
            parent=base_styles["Heading3"],
            fontName=bold_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceBefore=2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "normal": ParagraphStyle(
            name="MODO_Normal",
            parent=base_styles["Normal"],
            fontName=regular_font,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=2 * mm,
        ),
        "meta": ParagraphStyle(
            name="MODO_Meta",
            parent=base_styles["Normal"],
            fontName=regular_font,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=1 * mm,
        ),
        "option": ParagraphStyle(
            name="MODO_Option",
            parent=base_styles["Normal"],
            fontName=regular_font,
            fontSize=9.5,
            leading=13,
            leftIndent=4 * mm,
            firstLineIndent=-4 * mm,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=1.5 * mm,
        ),
        "correct_option": ParagraphStyle(
            name="MODO_CorrectOption",
            parent=base_styles["Normal"],
            fontName=bold_font,
            fontSize=9.5,
            leading=13,
            leftIndent=4 * mm,
            firstLineIndent=-4 * mm,
            textColor=colors.HexColor(
                "#166534"
            ),
            spaceAfter=1.5 * mm,
        ),
        "caption": ParagraphStyle(
            name="MODO_Caption",
            parent=base_styles["Normal"],
            fontName=regular_font,
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6B7280"
            ),
        ),
    }


def create_metadata_table(
    rows: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    data: list[list[Paragraph]] = []

    for label, value in rows:
        data.append(
            [
                Paragraph(
                    (
                        f"<b>"
                        f"{escape_reportlab(label)}"
                        f"</b>"
                    ),
                    styles["meta"],
                ),
                Paragraph(
                    prepare_paragraph_text(
                        value
                    ),
                    styles["meta"],
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            42 * mm,
            118 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#F3F4F6"
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.HexColor(
                        "#E5E7EB"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


def load_media_thumbnail(
    media: Any,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    """
    Загружает оригинал из R2
    и создаёт миниатюру для PDFошибке PDF остаётся читаемым.
    """
    r2_key = getattr(
        media,
        "r2_key",
        None,
    )

    if not r2_key:
        return []

    original_filename = str(
        getattr(
            media,
            "original_filename",
            "Изображение",
        )
        or "Изображение"
    )

    try:
        client = create_s3_client()

        response = client.get_object(
            Bucket=get_r2_bucket_name(),
            Key=normalize_r2_key(
                str(r2_key)
            ),
        )

        image_bytes = response[
            "Body"
        ].read()

        image_buffer = io.BytesIO(
            image_bytes
        )

        image = Image(
            image_buffer
        )

        source_width = float(
            image.imageWidth
        )

        source_height = float(
            image.imageHeight
        )

        if (
            source_width <= 0
            or source_height <= 0
        ):
            return []

        max_width = 75 * mm
        max_height = 55 * mm

        scale = min(
            max_width / source_width,
            max_height / source_height,
            1.0,
        )

        image.drawWidth = (
            source_width * scale
        )

        image.drawHeight = (
            source_height * scale
        )

        image.hAlign = "CENTER"

        caption = Paragraph(
            escape_reportlab(
                original_filename
            ),
            styles["caption"],
        )

        return [
            KeepTogether(
                [
                    image,
                    Spacer(
                        1,
                        1 * mm,
                    ),
                    caption,
                    Spacer(
                        1,
                        3 * mm,
                    ),
                ]
            )
        ]

    except Exception:
        logger.exception(
            "Failed to add image to PDF: %s",
            r2_key,
        )

        return [
            Paragraph(
                (
                    "[Изображение недоступно: "
                    f"{escape_reportlab(original_filename)}]"
                ),
                styles["meta"],
            )
        ]


def append_media_gallery(
    story: list[Any],
    question: Any,
    styles: dict[str, ParagraphStyle],
) -> None:
    media_files = list(
        getattr(
            question,
            "media_files",
            None,
        )
        or []
    )

    if not media_files:
        return

    story.append(
        Paragraph(
            "Изображения и схемы",
            styles["section"],
        )
    )

    for media in media_files:
        story.extend(
            load_media_thumbnail(
                media,
                styles,
            )
        )


def append_question(
    story: list[Any],
    question: Any,
    question_number: int,
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(
        Paragraph(
            f"Вопрос {question_number}",
            styles["question_title"],
        )
    )

    objective_label = (
        get_objective_label(
            question
        )
    )

    cognitive_level = (
        get_enum_value(
            getattr(
                question,
                "cognitive_level",
                None,
            )
        )
        or "Не указан"
    )

    story.append(
        Paragraph(
            (
                "ОРО: "
                f"{escape_reportlab(objective_label)}"
                " | Когнитивный уровень: "
                f"{escape_reportlab(cognitive_level)}"
            ),
            styles["meta"],
        )
    )

    resource_kz = getattr(
        question,
        "resource_kz",
        None,
    )

    resource_ru = getattr(
        question,
        "resource_ru",
        None,
    )

    if resource_kz or resource_ru:
        story.append(
            Paragraph(
                "Ресурсный блок",
                styles["section"],
            )
        )

        if resource_kz:
            story.append(
                Paragraph(
                    (
                        "<b>KZ:</b> "
                        + prepare_paragraph_text(
                            resource_kz
                        )
                    ),
                    styles["normal"],
                )
            )

        if resource_ru:
            story.append(
                Paragraph(
                    (
                        "<b>RU:</b> "
                        + prepare_paragraph_text(
                            resource_ru
                        )
                    ),
                    styles["normal"],
                )
            )

    story.append(
        Paragraph(
            "Текст вопроса",
            styles["section"],
        )
    )

    question_text_kz = getattr(
        question,
        "question_text_kz",
        None,
    )

    question_text_ru = getattr(
        question,
        "question_text_ru",
        None,
    )

    legacy_body = getattr(
        question,
        "body",
        None,
    )

    if question_text_kz:
        story.append(
            Paragraph(
                (
                    "<b>KZ:</b> "
                    + prepare_paragraph_text(
                        question_text_kz
                    )
                ),
                styles["normal"],
            )
        )

    if question_text_ru:
        story.append(
            Paragraph(
                (
                    "<b>RU:</b> "
                    + prepare_paragraph_text(
                        question_text_ru
                    )
                ),
                styles["normal"],
            )
        )

    if (
        not question_text_kz
        and not question_text_ru
        and legacy_body
    ):
        story.append(
            Paragraph(
                prepare_paragraph_text(
                    legacy_body
                ),
                styles["normal"],
            )
        )

    options = normalize_options(
        question
    )

    if options:
        story.append(
            Paragraph(
                "Варианты ответа",
                styles["section"],
            )
        )

        for option in options:
            option_key = escape_reportlab(
                option["key"]
            )

            option_style = (
                styles["correct_option"]
                if option["is_correct"]
                else styles["option"]
            )

            correct_label = (
                " [правильный ответ]"
                if option["is_correct"]
                else ""
            )

            story.append(
                Paragraph(
                    (
                        f"<b>{option_key}.</b> "
                        "KZ: "
                        f"{prepare_paragraph_text(option['text_kz'])}"
                        "<br/>"
                        "RU: "
                        f"{prepare_paragraph_text(option['text_ru'])}"
                        f"{escape_reportlab(correct_label)}"
                    ),
                    option_style,
                )
            )

    explanation_kz = getattr(
        question,
        "explanation_kz",
        None,
    )

    explanation_ru = getattr(
        question,
        "explanation_ru",
        None,
    )

    legacy_explanation = getattr(
        question,
        "explanation",
        None,
    )

    if (
        explanation_kz
        or explanation_ru
        or legacy_explanation
    ):
        story.append(
            Paragraph(
                "Пояснение",
                styles["section"],
            )
        )

        if explanation_kz:
            story.append(
                Paragraph(
                    (
                        "<b>KZ:</b> "
                        + prepare_paragraph_text(
                            explanation_kz
                        )
                    ),
                    styles["normal"],
                )
            )

        if explanation_ru:
            story.append(
                Paragraph(
                    (
                        "<b>RU:</b> "
                        + prepare_paragraph_text(
                            explanation_ru
                        )
                    ),
                    styles["normal"],
                )
            )

        if (
            not explanation_kz
            and not explanation_ru
            and legacy_explanation
        ):
            story.append(
                Paragraph(
                    prepare_paragraph_text(
                        legacy_explanation
                    ),
                    styles["normal"],
                )
            )

    append_media_gallery(
        story,
        question,
        styles,
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor(
                "#D1D5DB"
            ),
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


def generate_test_bank_pdf(
    questions: list[Any],
) -> bytes:
    """
    Создаёт legacy PDF отдельных вопросов.
    """
    regular_font, bold_font = (
        register_unicode_fonts()
    )

    styles = create_styles(
        regular_font,
        bold_font,
    )

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Банк тестовых заданий",
        author="MODO Platform",
    )

    story: list[Any] = [
        Paragraph(
            "Банк тестовых заданий",
            styles["title"],
        ),
        Paragraph(
            (
                "Количество вопросов: "
                f"{len(questions)}"
            ),
            styles["normal"],
        ),
        Spacer(
            1,
            5 * mm,
        ),
        PageBreak(),
    ]

    for index, question in enumerate(
        questions,
        start=1,
    ):
        append_question(
            story,
            question,
            index,
            styles,
        )

    document.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()


def generate_variants_test_bank_pdf(
    variants: list[Any],
) -> bytes:
    """
    Создаёт PDF выбранных вариантов.

    Для каждого варианта выводятся:
    - ФИО разработчика;
    - предмет;
    - класс;
    - верификатор;
    - куратор;
    - вопросы;
    - ответы;
    - пояснения;
    - изображения.
    """
    regular_font, bold_font = (
        register_unicode_fonts()
    )

    styles = create_styles(
        regular_font,
        bold_font,
    )

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Экспорт вариантов MODO",
        author="MODO Platform",
        subject="Банк вариантов",
    )

    total_questions = sum(
        len(
            getattr(
                variant,
                "questions",
                None,
            )
            or []
        )
        for variant in variants
    )

    story: list[Any] = [
        Paragraph(
            "Банк тестовых вариантов",
            styles["title"],
        ),
        Paragraph(
            (
                "Количество вариантов: "
                f"{len(variants)}"
                "<br/>"
                "Количество вопросов: "
                f"{total_questions}"
            ),
            styles["normal"],
        ),
        Spacer(
            1,
            5 * mm,
        ),
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#9CA3AF"
            ),
        ),
        PageBreak(),
    ]

    for variant_index, variant in enumerate(
        variants,
        start=1,
    ):
        variant_title = (
            getattr(
                variant,
                "title",
                None,
            )
            or f"Вариант {variant_index}"
        )

        story.append(
            Paragraph(
                (
                    f"Вариант {variant_index}: "
                    f"{escape_reportlab(variant_title)}"
                ),
                styles["variant_title"],
            )
        )

        metadata_rows = [
            (
                "ФИО разработчика",
                get_user_name(
                    getattr(
                        variant,
                        "developer",
                        None,
                    )
                ),
            ),
            (
                "Предмет",
                get_subject_title(
                    variant
                ),
            ),
            (
                "Класс",
                get_variant_class(
                    variant
                ),
            ),
            (
                "Верификатор",
                get_user_name(
                    getattr(
                        variant,
                        "reviewer",
                        None,
                    )
                ),
            ),
            (
                "Куратор",
                get_user_name(
                    getattr(
                        variant,
                        "curator",
                        None,
                    )
                ),
            ),
            (
                "Статус",
                get_enum_value(
                    getattr(
                        variant,
                        "status",
                        None,
                    )
                ),
            ),
        ]

        story.append(
            create_metadata_table(
                metadata_rows,
                styles,
            )
        )

        description = getattr(
            variant,
            "description",
            None,
        )

        if description:
            story.extend(
                [
                    Spacer(
                        1,
                        3 * mm,
                    ),
                    Paragraph(
                        (
                            "<b>Описание:</b> "
                            + prepare_paragraph_text(
                                description
                            )
                        ),
                        styles["normal"],
                    ),
                ]
            )

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        questions = list(
            getattr(
                variant,
                "questions",
                None,
            )
            or []
        )

        questions.sort(
            key=lambda question: (
                getattr(
                    question,
                    "order_number",
                    0,
                )
                or 0,
                getattr(
                    question,
                    "id",
                    0,
                )
                or 0,
            )
        )

        for fallback_number, question in enumerate(
            questions,
            start=1,
        ):
            question_number = (
                getattr(
                    question,
                    "order_number",
                    None,
                )
                or fallback_number
            )

            append_question(
                story,
                question,
                int(question_number),
                styles,
            )

        if variant_index < len(
            variants
        ):
            story.append(
                PageBreak()
            )

    document.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()