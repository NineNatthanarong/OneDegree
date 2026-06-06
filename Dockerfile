# syntax=docker/dockerfile:1.7
# OneDegree — single container: Next.js static frontend served by the FastAPI backend.

# ---------- 1. Build the frontend (Next.js static export) ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY Web/package.json Web/package-lock.json* ./
RUN npm ci
COPY Web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
# next.config.mjs sets output:"export" → emits the static site to /web/out
RUN npm run build

# ---------- 2. Python runtime serving API + frontend ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static
WORKDIR /app

COPY Server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY Server/app ./app
COPY Server/curriculum_database.json ./curriculum_database.json
# Built frontend from stage 1 → served by FastAPI at "/"
COPY --from=web /web/out ./static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
