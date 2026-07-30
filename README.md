# TestForge — Платформа разработки тестовых заданий

## Архитектура

```
testforge/
├── backend/                # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/v1/         # REST endpoints
│   │   ├── core/           # Config, DB, Security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # R2 storage, export (XLSX, PDF)
│   │   └── main.py         # FastAPI application
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React 18 + Vite + Tailwind
│   ├── src/
│   │   ├── components/     # Shared components
│   │   ├── contexts/       # AuthContext
│   │   ├── pages/          # Page components
│   │   ├── services/       # Axios API client
│   │   └── utils/          # LaTeX renderer, status helpers
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Ролевая модель (RBAC)

| Роль | Описание |
|------|----------|
| `DEVELOPER` | Создаёт/редактирует черновики, загружает медиа, отправляет на верификацию |
| `VERIFIER` | Проверяет вопросы, одбраживает или возвращает на доработку |
| `CURATOR` | Просматривает банк, формирует ZIP-выгрузку |

## Статусы вопросов

```
DRAFT → VERIFICATION → IN_BANK
                ↓
            REVISION → VERIFICATION
```

## Стек технологий

### Backend
- Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic
- Pydantic v2, PyJWT, passlib (bcrypt)
- boto3 (Cloudflare R2), openpyxl, reportlab

### Frontend
- React 18, Vite, TypeScript, Tailwind CSS
- React Router v6, Axios, Lucide React, KaTeX

### Инфраструктура
- PostgreSQL (Supabase / Render)
- Cloudflare R2 (S3-совместимое хранилище)
- Render (API + DB), Vercel (Frontend)

## Запуск локально

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройте .env
cp .env.example .env
# Отредактируйте .env с вашими ключами

# Запустите миграции
alembic upgrade head

# Запустите сервер
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
API Docs: http://localhost:8000/docs

## Ключевые эндпоинты

### Auth
- `POST /api/v1/auth/register` — регистрация
- `POST /api/v1/auth/login` — авторизация
- `GET /api/v1/auth/me` — текущий пользователь

### Questions
- `POST /api/v1/questions` — создать вопрос (DEVELOPER)
- `PUT /api/v1/questions/{id}` — обновить вопрос (DEVELOPER)
- `POST /api/v1/questions/{id}/submit` — отправить на верификацию (DEVELOPER)
- `GET /api/v1/questions/verification-queue` — очередь проверки (VERIFIER)
- `POST /api/v1/questions/{id}/review` — одобрить/вернуть (VERIFIER)
- `GET /api/v1/questions/bank` — банк заданий (все роли)
- `GET /api/v1/questions/my` — мои вопросы (DEVELOPER)

### Media
- `POST /api/v1/media/upload/{question_id}` — загрузить файл
- `DELETE /api/v1/media/{id}` — удалить файл

### Export
- `POST /api/v1/export/zip` — скачать ZIP (registry.xlsx + test_bank.pdf + media/)

## Формулы LaTeX

В тексте вопросов и вариантов ответов поддерживается LaTeX:
- Инлайн: `$E = mc^2$`
- Блочные: `$$\int_0^\infty e^{-x} dx = 1$$`

На фронтенде формулы рендерятся через KaTeX в реальном времени.
В PDF-экспорте формулы отображаются курсивом (для полноценного рендеринга можно интегрировать MathJax).

## Медиафайлы

- Загружаются в Cloudflare R2 **без сжатия** (оригинальное качество)
- На фронтенде отображаются с `object-contain` (без обрезки и искажений)
- В ZIP-экспорте выгружаются в папку `media/` как отдельные файлы
