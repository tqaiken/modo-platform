"""
PDF export via WeasyPrint (HTML → PDF).

LaTeX formulas are rendered as PNG images via matplotlib.
Logo is loaded from the web and embedded as a data URI.
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
# 1. LaTeX Rendering
# ============================================================

_latex_cache: dict[str, str | None] = {}


def _render_latex_to_data_uri(
    latex: str, fontsize: int = 14
) -> str | None:
    """Render a LaTeX formula to a base64 PNG data URI."""
    cache_key = f"{fontsize}:{latex}"
    if cache_key in _latex_cache:
        return _latex_cache[cache_key]

    try:
        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        fig.patch.set_alpha(0)
        ax.set_axis_off()
        ax.text(
            0.5, 0.5,
            f"${latex}$",
            fontsize=fontsize,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=200,
            bbox_inches="tight",
            pad_inches=0.05,
            transparent=True,
        )
        plt.close(fig)
        buf.seek(0)

        b64 = base64.b64encode(buf.read()).decode("ascii")
        data_uri = f"data:image/png;base64,{b64}"
        _latex_cache[cache_key] = data_uri
        return data_uri

    except Exception:
        logger.warning(
            "Failed to render LaTeX: %s", latex, exc_info=True
        )
        plt.close("all")
        _latex_cache[cache_key] = None
        return None


def _prepare_text(text: str | None) -> str:
    """
    Tokenise text: render LaTeX formulas as images,
    escape the rest as safe HTML.
    """
    if not text:
        return ""

    tokens: list[tuple[str, str]] = []
    pos = 0

    for m in re.finditer(
        r"\$\$(.+?)\$\$|\$(.+?)\$", text, re.DOTALL
    ):
        if m.start() > pos:
            tokens.append(("text", text[pos : m.start()]))

        if m.group(1) is not None:
            tokens.append(("block_latex", m.group(1).strip()))
        else:
            tokens.append(("inline_latex", m.group(2).strip()))

        pos = m.end()

    if pos < len(text):
        tokens.append(("text", text[pos:]))

    parts: list[str] = []

    for kind, content in tokens:
        if kind == "text":
            safe = html.escape(content).replace("\n", "<br>")
            parts.append(safe)

        elif kind == "block_latex":
            src = _render_latex_to_data_uri(content, fontsize=16)
            if src:
                alt = html.escape(content)
                parts.append(
                    f'<img src="{src}" '
                    f'style="display:block;margin:4px auto;'
                    f'height:1.6em;" alt="{alt}">'
                )
            else:
                parts.append(
                    f'<code class="lf">'
                    f"{html.escape(content)}</code>"
                )

        elif kind == "inline_latex":
            src = _render_latex_to_data_uri(content, fontsize=13)
            if src:
                alt = html.escape(content)
                parts.append(
                    f'<img src="{src}" '
                    f'style="display:inline-block;'
                    f'vertical-align:middle;'
                    f'height:1.2em;margin:0 2px;" '
                    f'alt="{alt}">'
                )
            else:
                parts.append(
                    f'<code class="lf">'
                    f"{html.escape(content)}</code>"
                )

    return "".join(parts)


# ============================================================
# 2. Logo
# ============================================================

_logo_cache: str | None = None


def _get_logo_data_uri() -> str:
    """Download logo and return as data URI."""
    global _logo_cache
    if _logo_cache is not None:
        return _logo_cache

    try:
        resp = httpx.get(
            LOGO_URL, timeout=10, follow_redirects=True
        )
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode("ascii")
        _logo_cache = f"data:{ct};base64,{b64}"
    except Exception:
        logger.warning("Failed to download logo from %s", LOGO_URL)
        _logo_cache = ""

    return _logo_cache


# ============================================================
# 3. Data Helpers
# ============================================================


def _enum_str(value: Any) -> str:
    if value is None:
        return "\u2014"
    v = getattr(value, "value", None)
    return str(v) if v is not None else str(value)


def _user_name(user: Any) -> str:
    if user is None:
        return "\u2014"
    for attr in ("full_name", "username"):
        val = getattr(user, attr, None)
        if val:
            return str(val)
    return "\u2014"


def _subject_title(variant: Any) -> str:
    subj = getattr(variant, "subject", None)
    if subj:
        t = getattr(subj, "title", None)
        if t:
            return str(t)
    return "\u2014"


def _variant_grade(variant: Any) -> str:
    for field in ("grade", "class_name", "school_class"):
        val = getattr(variant, field, None)
        if val:
            return str(val)
    return "\u2014"


def _objective_label(question: Any) -> str:
    obj = getattr(question, "learning_objective", None)
    if obj:
        code = str(getattr(obj, "code", "") or "")
        title = str(getattr(obj, "title_ru", "") or "")
        if code and title:
            return f"{code}: {title}"
        return code or title or "\u2014"
    return "\u2014"


def _normalize_options(question: Any) -> list[dict[str, Any]]:
    raw = getattr(question, "options", None) or []
    if not isinstance(raw, list):
        return []

    result: list[dict[str, Any]] = []
    for i, opt in enumerate(raw):
        if not isinstance(opt, dict):
            continue
        key = str(opt.get("key", chr(65 + i)) or chr(65 + i))
        kz = str(opt.get("text_kz", opt.get("text", "")) or "")
        ru = str(opt.get("text_ru", opt.get("text", "")) or "")
        result.append(
            {
                "key": key,
                "text_kz": _prepare_text(kz),
                "text_ru": _prepare_text(ru),
                "is_correct": opt.get("is_correct") is True,
            }
        )
    return result


# ============================================================
# 4. Media
# ============================================================


def _load_media_data_uri(media: Any) -> dict[str, str] | None:
    r2_key = getattr(media, "r2_key", None)
    if not r2_key:
        return None

    filename = str(
        getattr(media, "original_filename", "image") or "image"
    )

    try:
        client = create_s3_client()
        resp = client.get_object(
            Bucket=get_r2_bucket_name(),
            Key=normalize_r2_key(str(r2_key)),
        )
        data = resp["Body"].read()
        ct = (
            getattr(media, "content_type", None) or "image/png"
        )
        b64 = base64.b64encode(data).decode("ascii")
        return {
            "src": f"data:{ct};base64,{b64}",
            "alt": filename,
        }
    except Exception:
        logger.exception("Failed to load media: %s", r2_key)
        return {"src": "", "alt": filename}


# ============================================================
# 5. HTML / CSS Template
# ============================================================

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
/* ── Page Setup ─────────────────────────────── */
@page {
    size: A4;
    margin: 20mm 16mm 22mm 16mm;
    @bottom-center {
        content: "\2014  " counter(page) "  \2014";
        font-size: 8pt;
        color: #9ca3af;
    }
}
@page :first {
    @bottom-center { content: none; }
}

* { box-sizing: border-box; }

body {
    font-family: "Noto Sans", "DejaVu Sans",
                 "Liberation Sans", Arial, sans-serif;
    font-size: 10pt;
    color: #1f2937;
    line-height: 1.5;
    margin: 0;
    padding: 0;
}

/* ── Cover ──────────────────────────────────── */
.cover {
    text-align: center;
    padding-top: 70mm;
}
.cover .logo {
    width: 40mm;
    height: auto;
    margin-bottom: 10mm;
}
.cover h1 {
    font-size: 22pt;
    color: #1e3a5f;
    font-weight: 700;
    margin: 0 0 6mm 0;
}
.cover .divider {
    width: 50mm;
    height: 2px;
    background: #d1d5db;
    margin: 8mm auto;
}
.cover .stats {
    font-size: 11pt;
    color: #6b7280;
    line-height: 2;
}
.cover .date {
    font-size: 9pt;
    color: #9ca3af;
    margin-top: 50mm;
}

/* ── Variant Header ─────────────────────────── */
.vh {
    font-size: 15pt;
    font-weight: 700;
    color: #1e3a5f;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 3mm;
    margin-bottom: 5mm;
}

/* ── Metadata Table ─────────────────────────── */
.mt {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5mm;
    font-size: 9pt;
}
.mt td {
    padding: 2.5mm 3.5mm;
    border: 1px solid #e5e7eb;
    vertical-align: top;
}
.mt .l {
    width: 36%;
    background: #f3f4f6;
    font-weight: 600;
    color: #374151;
}
.mt .v { color: #1f2937; }

/* ── Description ────────────────────────────── */
.vd {
    font-size: 9.5pt;
    color: #4b5563;
    margin-bottom: 5mm;
    padding: 3mm 4mm;
    background: #f9fafb;
    border-left: 3px solid #d1d5db;
}

/* ── Question ───────────────────────────────── */
.q {
    margin-bottom: 5mm;
    padding-bottom: 4mm;
    border-bottom: 1px solid #e5e7eb;
}
.qt {
    font-size: 11pt;
    font-weight: 700;
    color: #111827;
    margin-bottom: 1mm;
}
.qm {
    font-size: 8.5pt;
    color: #6b7280;
    margin-bottom: 2.5mm;
}

/* ── Section Label ──────────────────────────── */
.s {
    font-size: 8.5pt;
    font-weight: 700;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-top: 2.5mm;
    margin-bottom: 1mm;
}

/* ── Content ────────────────────────────────── */
.c {
    font-size: 9.5pt;
    margin-bottom: 1.5mm;
    line-height: 1.6;
}
.lg {
    font-weight: 700;
    color: #2563eb;
}

/* ── Options ────────────────────────────────── */
.o {
    padding: 2mm 3mm 2mm 7mm;
    margin-bottom: 1.5mm;
    border: 1px solid #e5e7eb;
    border-radius: 1.5mm;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
.o .k {
    font-weight: 700;
    color: #4b5563;
}
.o.ok {
    background: #f0fdf4;
    border-color: #86efac;
    border-left: 3px solid #16a34a;
}
.o.ok .k { color: #16a34a; }
.bg {
    font-size: 8pt;
    color: #16a34a;
    font-weight: 700;
    margin-left: 2mm;
}

/* ── Explanation ────────────────────────────── */
.e {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 3px solid #f59e0b;
    padding: 2.5mm 3mm;
    margin-top: 2mm;
    border-radius: 1.5mm;
}
.e .s { color: #92400e; }

/* ── Media ──────────────────────────────────── */
.mw {
    text-align: center;
    margin: 2mm 0;
}
.mw img {
    max-width: 80mm;
    max-height: 50mm;
    height: auto;
}
.mc {
    font-size: 8pt;
    color: #9ca3af;
    margin-top: 1mm;
}

/* ── LaTeX Fallback ─────────────────────────── */
.lf {
    font-family: "Courier New", Courier, monospace;
    background: #f3f4f6;
    padding: 0.5mm 1.5mm;
    border-radius: 1mm;
    font-size: 9pt;
    color: #7c3aed;
}

/* ── Page Break ─────────────────────────────── */
.pb { page-break-before: always; }
</style>
</head>
<body>

<!-- ════════ COVER ════════ -->
<div class="cover">
    {% if logo_src %}
    <img src="{{ logo_src }}" class="logo" alt="Logo">
    {% endif %}
    <h1>{{ cover_title }}</h1>
    <div class="divider"></div>
    <div class="stats">
        Количество вариантов: {{ variant_count }}<br>
        Количество вопросов: {{ question_count }}
    </div>
    <div class="date">{{ generated_at }}</div>
</div>

<!-- ════════ VARIANTS ════════ -->
{% for v in variants %}
<div class="pb"></div>

<div class="vh">Вариант {{ v.number }}: {{ v.title }}</div>

<table class="mt">
    <tr><td class="l">ФИО разработчика</td><td class="v">{{ v.developer }}</td></tr>
    <tr><td class="l">Предмет</td><td class="v">{{ v.subject }}</td></tr>
    <tr><td class="l">Класс</td><td class="v">{{ v.grade }}</td></tr>
    <tr><td class="l">Верификатор</td><td class="v">{{ v.reviewer }}</td></tr>
    <tr><td class="l">Куратор</td><td class="v">{{ v.curator }}</td></tr>
    <tr><td class="l">Статус</td><td class="v">{{ v.status }}</td></tr>
</table>

{% if v.description %}
<div class="vd">{{ v.description|safe }}</div>
{% endif %}

{% for q in v.questions %}
<div class="question">
    <div class="qt">Вопрос {{ q.number }}</div>
    <div class="qm">ОРО: {{ q.objective }} | Когнитивный уровень: {{ q.cognitive_level }}</div>

    {% if q.resource_kz or q.resource_ru %}
    <div class="s">Ресурсный блок</div>
    {% if q.resource_kz %}<div class="c"><span class="lg">KZ:</span> {{ q.resource_kz|safe }}</div>{% endif %}
    {% if q.resource_ru %}<div class="c"><span class="lg">RU:</span> {{ q.resource_ru|safe }}</div>{% endif %}
    {% endif %}

    <div class="s">Текст вопроса</div>
    {% if q.text_kz %}<div class="c"><span class="lg">KZ:</span> {{ q.text_kz|safe }}</div>{% endif %}
    {% if q.text_ru %}<div class="c"><span class="lg">RU:</span> {{ q.text_ru|safe }}</div>{% endif %}

    {% if q.options %}
    <div class="s">Варианты ответа</div>
    {% for o in q.options %}
    <div class="o{% if o.is_correct %} ok{% endif %}">
        <span class="k">{{ o.key }}.</span>
        KZ: {{ o.text_kz|safe }} &nbsp;&middot;&nbsp;
        RU: {{ o.text_ru|safe }}
        {% if o.is_correct %}<span class="bg">✓ верный ответ</span>{% endif %}
    </div>
    {% endfor %}
    {% endif %}

    {% if q.explanation_kz or q.explanation_ru %}
    <div class="e">
        <div class="s">Пояснение</div>
        {% if q.explanation_kz %}<div class="c"><span class="lg">KZ:</span> {{ q.explanation_kz|safe }}</div>{% endif %}
        {% if q.explanation_ru %}<div class="c"><span class="lg">RU:</span> {{ q.explanation_ru|safe }}</div>{% endif %}
    </div>
    {% endif %}

    {% if q.media %}
    <div class="s">Изображения</div>
    {% for img in q.media %}
    <div class="mw">
        {% if img.src %}
        <img src="{{ img.src }}" alt="{{ img.alt }}">
        {% else %}
        <span class="lf">[Изображение недоступно: {{ img.alt }}]</span>
        {% endif %}
        <div class="mc">{{ img.alt }}</div>
    </div>
    {% endfor %}
    {% endif %}
</div>
{% endfor %}
{% endfor %}

</body>
</html>"""


# ============================================================
# 6. Data Preparation
# ============================================================


def _prepare_variant(variant: Any, index: int) -> dict[str, Any]:
    """Convert a Variant ORM object into a template-ready dict."""
    questions_raw = sorted(
        list(getattr(variant, "questions", None) or []),
        key=lambda q: (
            getattr(q, "order_number", 0) or 0,
            getattr(q, "id", 0) or 0,
        ),
    )

    q_list: list[dict[str, Any]] = []

    for qi, question in enumerate(questions_raw, start=1):
        order = getattr(question, "order_number", None) or qi

        # Bilingual text with legacy fallback
        text_kz = getattr(question, "question_text_kz", None)
        text_ru = getattr(question, "question_text_ru", None)
        legacy_body = getattr(question, "body", None)
        if not text_kz and not text_ru and legacy_body:
            text_ru = legacy_body

        # Explanation with legacy fallback
        expl_kz = getattr(question, "explanation_kz", None)
        expl_ru = getattr(question, "explanation_ru", None)
        legacy_expl = getattr(question, "explanation", None)
        if not expl_kz and not expl_ru and legacy_expl:
            expl_ru = legacy_expl

        media_files = sorted(
            list(getattr(question, "media_files", None) or []),
            key=lambda m: getattr(m, "id", 0),
        )

        q_list.append(
            {
                "number": int(order),
                "objective": _objective_label(question),
                "cognitive_level": _enum_str(
                    getattr(question, "cognitive_level", None)
                ),
                "resource_kz": _prepare_text(
                    getattr(question, "resource_kz", None)
                ),
                "resource_ru": _prepare_text(
                    getattr(question, "resource_ru", None)
                ),
                "text_kz": _prepare_text(text_kz),
                "text_ru": _prepare_text(text_ru),
                "options": _normalize_options(question),
                "explanation_kz": _prepare_text(expl_kz),
                "explanation_ru": _prepare_text(expl_ru),
                "media": [
                    m
                    for m in (
                        _load_media_data_uri(mf)
                        for mf in media_files
                    )
                    if m
                ],
            }
        )

    desc = getattr(variant, "description", None)

    return {
        "number": index,
        "title": getattr(variant, "title", None)
        or f"Вариант {index}",
        "description": _prepare_text(desc) if desc else "",
        "developer": _user_name(
            getattr(variant, "developer", None)
        ),
        "subject": _subject_title(variant),
        "grade": _variant_grade(variant),
        "reviewer": _user_name(
            getattr(variant, "reviewer", None)
        ),
        "curator": _user_name(
            getattr(variant, "curator", None)
        ),
        "status": _enum_str(
            getattr(variant, "status", None)
        ),
        "questions": q_list,
    }


# ============================================================
# 7. PDF Generation (public API)
# ============================================================


def generate_test_bank_pdf(questions: list[Any]) -> bytes:
    """
    Legacy export of individual questions
    (no variant grouping).
    """

    class _Pseudo:
        pass

    pseudo = _Pseudo()
    pseudo.title = "Вопросы из банка"
    pseudo.description = None
    pseudo.developer = None
    pseudo.reviewer = None
    pseudo.curator = None
    pseudo.subject = None
    pseudo.status = None
    pseudo.questions = questions

    return generate_variants_test_bank_pdf([pseudo])


def generate_variants_test_bank_pdf(
    variants: list[Any],
) -> bytes:
    """
    Generate a polished PDF for the given variants.
    """
    prepared = [
        _prepare_variant(v, i + 1)
        for i, v in enumerate(variants)
    ]
    total_q = sum(len(v["questions"]) for v in prepared)

    now = datetime.now(timezone.utc)
    generated_at = now.strftime("%d.%m.%Y %H:%M UTC")

    env = Environment(loader=BaseLoader(), autoescape=True)
    tpl = env.from_string(TEMPLATE)
    rendered = tpl.render(
        logo_src=_get_logo_data_uri(),
        cover_title="Банк тестовых вариантов",
        variant_count=len(prepared),
        question_count=total_q,
        generated_at=generated_at,
        variants=prepared,
    )

    pdf_bytes = HTML(string=rendered).write_pdf()
    return pdf_bytes