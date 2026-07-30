# Деплой TestForge

## Бесплатный стек ($0/мес)

| Сервис | Роль | План |
|--------|------|------|
| **Render** | Backend + PostgreSQL | Free (spins down after 15min) |
| **Vercel** | Frontend | Free (unlimited) |
| **Cloudflare R2** | Хранение медиа | 10 GB free |

---

## 1. Подготовка

### 1.1 Создайте аккаунты
- [render.com](https://render.com) — GitHub-авторизация
- [vercel.com](https://vercel.com) — GitHub-авторизация
- [cloudflare.com](https://cloudflare.com) — для R2

### 1.2 Настройте Cloudflare R2
1. Cloudflare Dashboard → R2 → Create Bucket → имя: `testforge-media`
2. Settings → Public Access → включить → скопировать Public URL
3. Manage R2 API Tokens → Create Token:
   - Permission: Object Read & Write
   - Specify bucket: `testforge-media`
   - Сохраните Access Key ID и Secret Access Key

---

## 2. Деплой Backend (Render)

### 2.1 Push в GitHub
```bash
cd /path/to/testforge
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOU/testforge.git
git push -u origin main
```

### 2.2 Создайте Blueprint
1. Render → New → Blueprint
2. Connect GitHub repo
3. Render найдёт `render.yaml` → Apply
4. Задеплоится автоматически:
   - PostgreSQL база
   - FastAPI backend с миграциями

### 2.3 Задайте секреты R2
В Render Dashboard → testforge-api → Environment:
```
R2_ENDPOINT_URL = https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID = <your-key>
R2_SECRET_ACCESS_KEY = <your-secret>
R2_BUCKET_NAME = testforge-media
R2_PUBLIC_URL = https://pub-<hash>.r2.dev
```

### 2.4 Seed данных
В Render Dashboard → testforge-api → Shell:
```bash
python -m app.seed
```

---

## 3. Деплой Frontend (Vercel)

### 3.1 Подключите репозиторий
1. Vercel → Add New Project
2. Import GitHub repo
3. Root Directory: `frontend`
4. Framework: Vite (auto-detected)
5. Deploy

### 3.2 Настройте API URL
В Vercel Dashboard → Settings → Environment Variables:
```
VITE_API_URL = https://testforge-api.onrender.com
```

Или обновите `vercel.json` → destination на ваш Render URL.

### 3.3 Обновите CORS
В Render Dashboard → testforge-api → Environment:
```
CORS_ORIGINS = ["https://your-project.vercel.app"]
```

---

## 4. Проверка

1. Откройте `https://your-project.vercel.app`
2. Войдите как `curator@testforge.kz` / `curator123`
3. Создайте вопрос от имени разработчика
4. Отправьте на верификацию
5. Одобрите от имени верификатора
6. Выгрузите ZIP от имени куратора

---

## 5. Troubleshooting

| Проблема | Решение |
|----------|---------|
| Render spinnig down | Free plan sleeps after 15min. Первый запрос просыпается ~30с. Upgrade to $7/мес для always-on. |
| CORS errors | Проверьте CORS_ORIGINS в Render, должен совпадать с Vercel URL |
| R2 upload fails | Проверьте R2 token permissions (Object Read & Write) |
| DB connection refused | Render internal DB URL работает только внутри Render. Для локального теста используйте внешний DB URL. |
| Alembic error | Убедитесь что миграция запускается до seed: `alembic upgrade head && python -m app.seed` |
