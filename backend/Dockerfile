FROM python:3.11-slim

# System deps: fonts + WeasyPrint (pango, cairo, gdk-pixbuf) + Postgres
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libcairo2 \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]