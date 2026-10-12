"""
PDF export via WeasyPrint (HTML to PDF).

LaTeX formulas are rendered as PNG images via matplotlib.
The logo and question media are embedded as data URIs.

The generated document is a confidential curator report.
"""

import base64
import html
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from jinja2 import BaseLoader, Environment
from weasyprint import HTML

from app.services.r2 import (
    create_s3_client,
    get_r2_bucket_name,
    normalize_r2_key,
)


logger = logging.getLogger(__name__)

LOGO_URL = "https://modo2026.vercel.app/logo.png"


# ============================================================
# 1. LaTeX rendering
# ============================================================

_latex_cache: dict[str, str | None] = {}


def _render_latex_to_data_uri(
    latex: str,
    fontsize: int = 14,
) -> str | None:
    """
    Render a LaTeX expression as a base64 PNG data URI.
    """
    cache_key = f"{fontsize}:{latex}"

    if cache_key in _latex_cache:
        return _latex_cache[cache_key]

    figure = None

    try:
        figure, axis = plt.subplots(
            figsize=(
                0.01,
                0.01,
            )
        )

        figure.patch.set_alpha(0)
        axis.set_axis_off()

        axis.text(
            0.5,
            0.5,
            f"${latex}$",
            fontsize=fontsize,
            ha="center",
            va="center",
            transform=axis.transAxes,
        )

        buffer = io.BytesIO()

        figure.savefig(
            buffer,
            format="png",
            dpi=200,
            bbox_inches="tight",
            pad_inches=0.05,
            transparent=True,
        )

        buffer.seek(0)

        encoded = base64.b64encode(
            buffer.read()
        ).decode("ascii")

        data_uri = (
            "data:image/png;base64,"
            f"{encoded}"
        )

        _latex_cache[cache_key] = (
            data_uri
        )

        return data_uri

    except Exception:
        logger.warning(
            "Failed to render LaTeX: %s",
            latex,
            exc_info=True,
        )

        _latex_cache[cache_key] = None

        return None

    finally:
        if figure is not None:
            plt.close(
                figure
            )


def _prepare_text(
    text: str | None,
) -> str:
    """
    Convert plain text to safe HTML.

    Inline LaTeX:
        $x + y$

    Block LaTeX:
        $$x + y$$

    Non-LaTeX text is escaped before being included
    in the HTML document.
    """
    if not text:
        return ""

    tokens: list[
        tuple[
            str,
            str,
        ]
    ] = []

    position = 0

    for match in re.finditer(
        r"\$\$(.+?)\$\$|\$(.+?)\$",
        text,
        re.DOTALL,
    ):
        if match.start() > position:
            tokens.append(
                (
                    "text",
                    text[
                        position:
                        match.start()
                    ],
                )
            )

        if match.group(1) is not None:
            tokens.append(
                (
                    "block_latex",
                    match.group(1).strip(),
                )
            )
        else:
            tokens.append(
                (
                    "inline_latex",
                    match.group(2).strip(),
                )
            )

        position = match.end()

    if position < len(text):
        tokens.append(
            (
                "text",
                text[position:],
            )
        )

    parts: list[str] = []

    for kind, content in tokens:
        if kind == "text":
            safe_text = html.escape(
                content
            ).replace(
                "\n",
                "<br>",
            )

            parts.append(
                safe_text
            )

            continue

        if kind == "block_latex":
            source = (
                _render_latex_to_data_uri(
                    content,
                    fontsize=16,
                )
            )

            if source is not None:
                escaped_source = html.escape(
                    source,
                    quote=True,
                )

                escaped_alt = html.escape(
                    content,
                    quote=True,
                )

                parts.append(
                    '<img '
                    f'src="{escaped_source}" '
                    f'alt="{escaped_alt}" '
                    'class="latex-block">'
                )
            else:
                parts.append(
                    '<code class="latex-fallback">'
                    f"{html.escape(content)}"
                    "</code>"
                )

            continue

        if kind == "inline_latex":
            source = (
                _render_latex_to_data_uri(
                    content,
                    fontsize=13,
                )
            )

            if source is not None:
                escaped_source = html.escape(
                    source,
                    quote=True,
                )

                escaped_alt = html.escape(
                    content,
                    quote=True,
                )

                parts.append(
                    '<img '
                    f'src="{escaped_source}" '
                    f'alt="{escaped_alt}" '
                    'class="latex-inline">'
                )
            else:
                parts.append(
                    '<code class="latex-fallback">'
                    f"{html.escape(content)}"
                    "</code>"
                )

    return "".join(
        parts
    )


# ============================================================
# 2. Logo
# ============================================================

_logo_cache: str | None = None


def _get_logo_data_uri() -> str:
    """
    Download the application logo and return a data URI.

    PDF generation continues without the logo if the request
    fails or the response is not an image.
    """
    global _logo_cache

    if _logo_cache is not None:
        return _logo_cache

    try:
        response = httpx.get(
            LOGO_URL,
            timeout=10,
            follow_redirects=True,
        )

        response.raise_for_status()

        content_type = (
            response.headers.get(
                "content-type",
                "image/png",
            )
            .split(
                ";",
                maxsplit=1,
            )[0]
            .strip()
            .lower()
        )

        if not content_type.startswith(
            "image/"
        ):
            raise ValueError(
                "Logo response is not an image."
            )

        encoded = base64.b64encode(
            response.content
        ).decode("ascii")

        _logo_cache = (
            f"data:{content_type};"
            f"base64,{encoded}"
        )

    except Exception:
        logger.warning(
            "Failed to download logo from %s",
            LOGO_URL,
            exc_info=True,
        )

        _logo_cache = ""

    return _logo_cache


# ============================================================
# 3. Data helpers
# ============================================================

VARIANT_STATUS_LABELS = {
    "DRAFT": "Черновик",
    "VERIFICATION": "На верификации",
    "REVISION": "На доработке",
    "APPROVED": "Утверждён",
    "IN_BANK": "В банке",
}


COGNITIVE_LEVEL_LABELS = {
    "BASIC": "Базовый",
    "MEDIUM": "Средний",
    "HIGH": "Высокий",
}


def _enum_str(
    value: Any,
) -> str:
    """
    Convert an enum or another value to text.
    """
    if value is None:
        return "—"

    enum_value = getattr(
        value,
        "value",
        None,
    )

    if enum_value is not None:
        return str(
            enum_value
        )

    return str(
        value
    )


def _variant_status_label(
    value: Any,
) -> str:
    """
    Return a localized variant status.
    """
    raw_value = _enum_str(
        value
    )

    return VARIANT_STATUS_LABELS.get(
        raw_value,
        raw_value,
    )


def _cognitive_level_label(
    value: Any,
) -> str:
    """
    Return a localized cognitive level.
    """
    raw_value = _enum_str(
        value
    )

    return COGNITIVE_LEVEL_LABELS.get(
        raw_value,
        raw_value,
    )


def _user_name(
    user: Any,
) -> str:
    """
    Return the most useful display name of a user.
    """
    if user is None:
        return "—"

    for attribute_name in (
        "full_name",
        "username",
    ):
        value = getattr(
            user,
            attribute_name,
            None,
        )

        if value:
            return str(
                value
            )

    user_id = getattr(
        user,
        "id",
        None,
    )

    if user_id is not None:
        return (
            f"Пользователь #{user_id}"
        )

    return "—"


def _subject_title(
    variant: Any,
) -> str:
    """
    Return the subject title assigned to a variant.
    """
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
            return str(
                title
            )

    subject_id = getattr(
        variant,
        "subject_id",
        None,
    )

    if subject_id is not None:
        return (
            f"Предмет #{subject_id}"
        )

    return "—"


def _variant_grade(
    variant: Any,
) -> str:
    """
    Return the variant grade.

    Legacy field names remain as fallbacks for compatibility
    with previously created pseudo-objects.
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

        if value is not None:
            return str(
                value
            )

    return "—"


def _objective_label(
    question: Any,
) -> str:
    """
    Return the learning-objective code and Russian title.
    """
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

        title = str(
            getattr(
                objective,
                "title_ru",
                "",
            )
            or ""
        )

        if code and title:
            return (
                f"{code}: {title}"
            )

        return (
            code
            or title
            or "—"
        )

    objective_id = getattr(
        question,
        "learning_objective_id",
        None,
    )

    if objective_id is not None:
        return (
            f"ОРО #{objective_id}"
        )

    return "—"


def _normalize_options(
    question: Any,
) -> list[dict[str, Any]]:
    """
    Normalize bilingual answer options for the template.
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

    normalized_options: list[
        dict[str, Any]
    ] = []

    for index, option in enumerate(
        raw_options
    ):
        if not isinstance(
            option,
            dict,
        ):
            continue

        default_key = chr(
            65 + index
        )

        key = str(
            option.get(
                "key",
                default_key,
            )
            or default_key
        )

        text_kz = str(
            option.get(
                "text_kz",
                option.get(
                    "text",
                    "",
                ),
            )
            or ""
        )

        text_ru = str(
            option.get(
                "text_ru",
                option.get(
                    "text",
                    "",
                ),
            )
            or ""
        )

        normalized_options.append(
            {
                "key": key,
                "text_kz": (
                    _prepare_text(
                        text_kz
                    )
                ),
                "text_ru": (
                    _prepare_text(
                        text_ru
                    )
                ),
                "is_correct": (
                    option.get(
                        "is_correct"
                    )
                    is True
                ),
            }
        )

    return normalized_options


# ============================================================
# 4. Media
# ============================================================


def _load_media_data_uri(
    media: Any,
) -> dict[str, str] | None:
    """
    Load question media from Cloudflare R2 as a data URI.
    """
    r2_key = getattr(
        media,
        "r2_key",
        None,
    )

    if not r2_key:
        return None

    filename = str(
        getattr(
            media,
            "original_filename",
            "image",
        )
        or "image"
    )

    try:
        client = create_s3_client()

        response = client.get_object(
            Bucket=get_r2_bucket_name(),
            Key=normalize_r2_key(
                str(
                    r2_key
                )
            ),
        )

        data = response[
            "Body"
        ].read()

        content_type = str(
            getattr(
                media,
                "content_type",
                None,
            )
            or "image/png"
        ).split(
            ";",
            maxsplit=1,
        )[0].strip().lower()

        if not content_type.startswith(
            "image/"
        ):
            logger.warning(
                "Skipped non-image media %s with content type %s",
                r2_key,
                content_type,
            )

            return {
                "src": "",
                "alt": filename,
            }

        encoded = base64.b64encode(
            data
        ).decode("ascii")

        return {
            "src": (
                f"data:{content_type};"
                f"base64,{encoded}"
            ),
            "alt": filename,
        }

    except Exception:
        logger.exception(
            "Failed to load media: %s",
            r2_key,
        )

        return {
            "src": "",
            "alt": filename,
        }


# ============================================================
# 5. HTML and CSS template
# ============================================================

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
@page {
    size: A4;
    margin: 20mm 16mm 22mm 16mm;
    @bottom-center {
        content: "\\2014  " counter(page) "  \\2014";
        font-size: 8pt;
        color: #9ca3af;
    }
}
@page :first {
    @bottom-center { content: none; }
}
* { box-sizing: border-box; }
body {
    font-family: "Noto Sans", "DejaVu Sans", "Liberation Sans", Arial, sans-serif;
    font-size: 10pt;
    color: #1f2937;
    line-height: 1.5;
    margin: 0;
    padding: 0;
}
.document-header {
    text-align: center;
    margin-bottom: 7mm;
    break-inside: avoid;
    page-break-inside: avoid;
}
.document-header .logo {
    display: block;
    width: 28mm;
    max-height: 20mm;
    height: auto;
    object-fit: contain;
    margin: 0 auto 4mm auto;
}
.document-header h1 {
    font-size: 18pt;
    color: #1e3a5f;
    font-weight: 700;
    margin: 0 0 2mm 0;
}
.document-summary {
    font-size: 9pt;
    color: #6b7280;
    line-height: 1.6;
}
.confidential {
    display: inline-block;
    margin-top: 3mm;
    padding: 1.5mm 3mm;
    border: 1px solid #fecaca;
    background: #fef2f2;
    color: #991b1b;
    font-size: 8pt;
    font-weight: 700;
    border-radius: 1.5mm;
}
.variant-page { page-break-before: always; }
.variant-page.first-variant { page-break-before: auto; }
.variant-overview {
    break-inside: avoid;
    page-break-inside: avoid;
}
.variant-heading {
    break-after: avoid;
    page-break-after: avoid;
}
.variant-title {
    font-size: 15pt;
    font-weight: 700;
    color: #1e3a5f;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 3mm;
    margin-bottom: 5mm;
}
.metadata-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5mm;
    font-size: 9pt;
    break-inside: avoid;
    page-break-inside: avoid;
}
.metadata-table td {
    padding: 2.5mm 3.5mm;
    border: 1px solid #e5e7eb;
    vertical-align: top;
}
.metadata-table .label {
    width: 36%;
    background: #f3f4f6;
    font-weight: 600;
    color: #374151;
}
.metadata-table .value { color: #1f2937; }
.variant-description {
    font-size: 9.5pt;
    color: #4b5563;
    padding: 3mm 4mm;
    background: #f9fafb;
    border-left: 3px solid #d1d5db;
    overflow-wrap: anywhere;
}
.question {
    page-break-before: always;
    break-before: page;
    margin: 0;
    padding: 0;
    border: 0;
}
.question-leading {
    break-inside: avoid;
    page-break-inside: avoid;
}
.question-title {
    font-size: 11pt;
    font-weight: 700;
    color: #1e3a5f;
    background: #eff6ff;
    border-left: 3px solid #2563eb;
    padding: 2.5mm 3mm;
    margin-bottom: 1.5mm;
}
.question-metadata {
    font-size: 8.5pt;
    color: #6b7280;
    margin-bottom: 2.5mm;
}
.section-label {
    font-size: 8.5pt;
    font-weight: 700;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-top: 2.5mm;
    margin-bottom: 1mm;
}
.content {
    font-size: 9.5pt;
    margin-bottom: 1.5mm;
    line-height: 1.6;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.language-label { font-weight: 700; color: #2563eb; }
.options-label, .media-label {
    break-after: avoid;
    page-break-after: avoid;
}
.option {
    padding: 2.5mm 3mm;
    margin-bottom: 1.8mm;
    border: 1px solid #e5e7eb;
    border-radius: 1.5mm;
    font-size: 9.5pt;
    break-inside: avoid;
    page-break-inside: avoid;
}
.option-key { font-weight: 700; color: #4b5563; }
.option.correct {
    background: #f0fdf4;
    border-color: #86efac;
    border-left: 3px solid #16a34a;
}
.option.correct .option-key { color: #15803d; }
.option-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 3mm;
    margin-bottom: 1mm;
}
.option-language {
    line-height: 1.5;
    margin-top: 0.8mm;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.correct-label {
    font-size: 8pt;
    color: #15803d;
    font-weight: 700;
    white-space: nowrap;
}
.explanation {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 3px solid #f59e0b;
    padding: 2.5mm 3mm;
    margin-top: 2mm;
    border-radius: 1.5mm;
}
.explanation .section-label { color: #92400e; margin-top: 0; }
.explanation-content {
    break-inside: avoid;
    page-break-inside: avoid;
}
.media-item {
    text-align: center;
    margin: 3mm 0;
    break-inside: avoid;
    page-break-inside: avoid;
}
.media-item img {
    display: block;
    max-width: 100%;
    max-height: 70mm;
    width: auto;
    height: auto;
    margin: 0 auto;
    object-fit: contain;
}
.media-caption {
    font-size: 8pt;
    color: #6b7280;
    margin-top: 1mm;
    overflow-wrap: anywhere;
}
.latex-block {
    display: block;
    height: 1.6em;
    width: auto;
    max-width: 100%;
    margin: 4px auto;
}
.latex-inline {
    display: inline-block;
    vertical-align: middle;
    height: 1.2em;
    width: auto;
    max-width: 100%;
    margin: 0 2px;
}
.latex-fallback {
    font-family: "Courier New", Courier, monospace;
    background: #f3f4f6;
    padding: 0.5mm 1.5mm;
    border-radius: 1mm;
    font-size: 9pt;
    color: #7c3aed;
}
</style>
</head>
<body>
{% for variant in variants %}
<section class="variant-page{% if loop.first %} first-variant{% endif %}">
    <div class="variant-overview">
        {% if loop.first %}
        <div class="document-header">
            {% if logo_src %}
            <img src="{{ logo_src }}" class="logo" alt="Логотип МОДО">
            {% endif %}
            <h1>{{ cover_title }}</h1>
            <div class="document-summary">
                Количество вариантов: {{ variant_count }} |
                Количество вопросов: {{ question_count }} |
                Сформировано: {{ generated_at }}
            </div>
            <div class="confidential">Конфиденциальный служебный документ</div>
        </div>
        {% endif %}

        <div class="variant-heading">
            <div class="variant-title">
                Вариант {{ variant.number }}: {{ variant.title }}
            </div>
            <table class="metadata-table">
                <tr><td class="label">ФИО разработчика</td><td class="value">{{ variant.developer }}</td></tr>
                <tr><td class="label">Предмет</td><td class="value">{{ variant.subject }}</td></tr>
                <tr><td class="label">Класс</td><td class="value">{{ variant.grade }}</td></tr>
                <tr><td class="label">Верификатор</td><td class="value">{{ variant.reviewer }}</td></tr>
                <tr><td class="label">Куратор</td><td class="value">{{ variant.curator }}</td></tr>
                <tr><td class="label">Статус</td><td class="value">{{ variant.status }}</td></tr>
            </table>
        </div>

        {% if variant.description %}
        <div class="variant-description">{{ variant.description|safe }}</div>
        {% endif %}
    </div>

    {% for question in variant.questions %}
    <article class="question">
        <div class="question-leading">
            <div class="question-title">Вопрос {{ question.number }}</div>
            <div class="question-metadata">
                ОРО: {{ question.objective }} |
                Когнитивный уровень: {{ question.cognitive_level }}
            </div>

            {% if question.resource_kz or question.resource_ru %}
            <div class="section-label">Ресурсный блок</div>
            {% if question.resource_kz %}
            <div class="content"><span class="language-label">KZ:</span> {{ question.resource_kz|safe }}</div>
            {% endif %}
            {% if question.resource_ru %}
            <div class="content"><span class="language-label">RU:</span> {{ question.resource_ru|safe }}</div>
            {% endif %}
            {% endif %}

            <div class="section-label">Текст вопроса</div>
            {% if question.text_kz %}
            <div class="content"><span class="language-label">KZ:</span> {{ question.text_kz|safe }}</div>
            {% endif %}
            {% if question.text_ru %}
            <div class="content"><span class="language-label">RU:</span> {{ question.text_ru|safe }}</div>
            {% endif %}
        </div>

        {% if question.options %}
        <div class="section-label options-label">Варианты ответа</div>
        {% for option in question.options %}
        <div class="option{% if option.is_correct %} correct{% endif %}">
            <div class="option-header">
                <span class="option-key">Ответ {{ option.key }}</span>
                {% if option.is_correct %}<span class="correct-label">✓ Верный ответ</span>{% endif %}
            </div>
            {% if option.text_kz %}
            <div class="option-language"><span class="language-label">KZ:</span> {{ option.text_kz|safe }}</div>
            {% endif %}
            {% if option.text_ru %}
            <div class="option-language"><span class="language-label">RU:</span> {{ option.text_ru|safe }}</div>
            {% endif %}
        </div>
        {% endfor %}
        {% endif %}

        {% if question.explanation_kz or question.explanation_ru %}
        <div class="explanation">
            <div class="section-label">Пояснение</div>
            <div class="explanation-content">
                {% if question.explanation_kz %}
                <div class="content"><span class="language-label">KZ:</span> {{ question.explanation_kz|safe }}</div>
                {% endif %}
                {% if question.explanation_ru %}
                <div class="content"><span class="language-label">RU:</span> {{ question.explanation_ru|safe }}</div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if question.media %}
        <div class="section-label media-label">Изображения</div>
        {% for image in question.media %}
        <div class="media-item">
            {% if image.src %}
            <img src="{{ image.src }}" alt="{{ image.alt }}">
            {% else %}
            <span class="latex-fallback">[Изображение недоступно: {{ image.alt }}]</span>
            {% endif %}
            <div class="media-caption">{{ image.alt }}</div>
        </div>
        {% endfor %}
        {% endif %}
    </article>
    {% endfor %}
</section>
{% endfor %}
</body>
</html>"""

# ============================================================
# 6. Data preparation
# ============================================================


def _prepare_variant(
    variant: Any,
    index: int,
) -> dict[str, Any]:
    """
    Convert a Variant ORM object to template-ready data.
    """
    questions_raw = sorted(
        list(
            getattr(
                variant,
                "questions",
                None,
            )
            or []
        ),
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
        ),
    )

    prepared_questions: list[
        dict[str, Any]
    ] = []

    for fallback_order, question in enumerate(
        questions_raw,
        start=1,
    ):
        order_number = (
            getattr(
                question,
                "order_number",
                None,
            )
            or fallback_order
        )

        text_kz = getattr(
            question,
            "question_text_kz",
            None,
        )

        text_ru = getattr(
            question,
            "question_text_ru",
            None,
        )

        legacy_body = getattr(
            question,
            "body",
            None,
        )

        if (
            not text_kz
            and not text_ru
            and legacy_body
        ):
            text_ru = legacy_body

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
            not explanation_kz
            and not explanation_ru
            and legacy_explanation
        ):
            explanation_ru = (
                legacy_explanation
            )

        media_files = sorted(
            list(
                getattr(
                    question,
                    "media_files",
                    None,
                )
                or []
            ),
            key=lambda media: (
                getattr(
                    media,
                    "id",
                    0,
                )
                or 0
            ),
        )

        prepared_media = [
            loaded_media
            for loaded_media in (
                _load_media_data_uri(
                    media
                )
                for media in media_files
            )
            if loaded_media is not None
        ]

        prepared_questions.append(
            {
                "number": int(
                    order_number
                ),
                "objective": (
                    _objective_label(
                        question
                    )
                ),
                "cognitive_level": (
                    _cognitive_level_label(
                        getattr(
                            question,
                            "cognitive_level",
                            None,
                        )
                    )
                ),
                "resource_kz": (
                    _prepare_text(
                        getattr(
                            question,
                            "resource_kz",
                            None,
                        )
                    )
                ),
                "resource_ru": (
                    _prepare_text(
                        getattr(
                            question,
                            "resource_ru",
                            None,
                        )
                    )
                ),
                "text_kz": (
                    _prepare_text(
                        text_kz
                    )
                ),
                "text_ru": (
                    _prepare_text(
                        text_ru
                    )
                ),
                "options": (
                    _normalize_options(
                        question
                    )
                ),
                "explanation_kz": (
                    _prepare_text(
                        explanation_kz
                    )
                ),
                "explanation_ru": (
                    _prepare_text(
                        explanation_ru
                    )
                ),
                "media": prepared_media,
            }
        )

    description = getattr(
        variant,
        "description",
        None,
    )

    title = (
        getattr(
            variant,
            "title",
            None,
        )
        or f"Вариант {index}"
    )

    return {
        "number": index,
        "title": str(
            title
        ),
        "description": (
            _prepare_text(
                description
            )
            if description
            else ""
        ),
        "developer": (
            _user_name(
                getattr(
                    variant,
                    "developer",
                    None,
                )
            )
        ),
        "subject": (
            _subject_title(
                variant
            )
        ),
        "grade": (
            _variant_grade(
                variant
            )
        ),
        "reviewer": (
            _user_name(
                getattr(
                    variant,
                    "reviewer",
                    None,
                )
            )
        ),
        "curator": (
            _user_name(
                getattr(
                    variant,
                    "curator",
                    None,
                )
            )
        ),
        "status": (
            _variant_status_label(
                getattr(
                    variant,
                    "status",
                    None,
                )
            )
        ),
        "questions": (
            prepared_questions
        ),
    }


# ============================================================
# 7. PDF generation
# ============================================================


def generate_test_bank_pdf(
    questions: list[Any],
) -> bytes:
    """
    Generate the legacy export of individual questions.

    The function remains available for compatibility with
    the legacy export endpoint.
    """

    class _PseudoVariant:
        pass

    pseudo_variant = (
        _PseudoVariant()
    )

    pseudo_variant.title = (
        "Вопросы из банка"
    )

    pseudo_variant.description = None
    pseudo_variant.grade = None
    pseudo_variant.developer = None
    pseudo_variant.reviewer = None
    pseudo_variant.curator = None
    pseudo_variant.subject = None
    pseudo_variant.subject_id = None
    pseudo_variant.status = None

    pseudo_variant.questions = (
        questions
    )

    return (
        generate_variants_test_bank_pdf(
            [
                pseudo_variant,
            ]
        )
    )


def generate_variants_test_bank_pdf(
    variants: list[Any],
) -> bytes:
    """
    Generate a confidential curator PDF for variants.
    """
    prepared_variants = [
        _prepare_variant(
            variant,
            index,
        )
        for index, variant in enumerate(
            variants,
            start=1,
        )
    ]

    total_questions = sum(
        len(
            variant[
                "questions"
            ]
        )
        for variant in prepared_variants
    )

    generated_at = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%d.%m.%Y %H:%M UTC"
        )
    )

    environment = Environment(
        loader=BaseLoader(),
        autoescape=True,
    )

    template = (
        environment.from_string(
            TEMPLATE
        )
    )

    rendered_html = template.render(
        logo_src=(
            _get_logo_data_uri()
        ),
        cover_title=(
            "Банк тестовых вариантов"
        ),
        variant_count=len(
            prepared_variants
        ),
        question_count=(
            total_questions
        ),
        generated_at=(
            generated_at
        ),
        variants=(
            prepared_variants
        ),
    )

    pdf_bytes = HTML(
        string=rendered_html,
        base_url=None,
    ).write_pdf()

    if not pdf_bytes.startswith(
        b"%PDF"
    ):
        raise RuntimeError(
            "WeasyPrint returned invalid PDF data."
        )

    return pdf_bytes