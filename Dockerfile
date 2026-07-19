# syntax=docker/dockerfile:1.7
# OneDegree — single container: Next.js static frontend served by the FastAPI backend.

# ---------- 1. Build the frontend (Next.js static export) ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY Web/package.json Web/package-lock.json* ./
# Resilience against a flaky build→registry network. The Docker Desktop network
# resets CONCURRENT connections under load (ECONNRESET / aborted), so serialize
# npm to a single socket and let it retry patiently; individual fetches can take
# 2min+ on a degraded link but complete one-at-a-time.
ENV NPM_CONFIG_MAXSOCKETS=1 \
    NPM_CONFIG_FETCH_RETRIES=8 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=5000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=180000 \
    NPM_CONFIG_FETCH_TIMEOUT=600000
# npm's own retries can still be exhausted by repeated ECONNRESETs, so wrap npm ci
# in a shell retry loop and keep an npm cache mount — retries reuse tarballs that
# already downloaded, so the install converges instead of restarting from zero.
RUN --mount=type=cache,target=/root/.npm \
    n=0; until npm ci; do \
      n=$((n+1)); \
      if [ "$n" -ge 8 ]; then echo "npm ci failed after $n attempts" >&2; exit 1; fi; \
      echo "npm ci attempt $n hit a network error; retrying in 10s..." >&2; \
      sleep 10; \
    done
COPY Web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
# next.config.mjs sets output:"export" → emits the static site to /web/out
RUN npm run build

# ---------- 2. Python runtime serving API + frontend ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    # Resilience against slow/flaky PyPI CDN reads (default socket timeout is
    # only 15s; on a degraded link a single read can take 2min+, so be patient).
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10
WORKDIR /app

COPY Server/requirements.txt ./requirements.txt
# pip does NOT retry a connection that breaks mid-download (IncompleteRead), so a
# flaky link aborts the whole install. Wrap it in a retry loop and keep a pip
# cache mount so wheels that already downloaded persist across attempts — each
# retry only refetches what's left, converging fast even on an unstable network.
# The cache mount lives outside the image, so it doesn't bloat the final layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    n=0; until pip install -r requirements.txt; do \
      n=$((n+1)); \
      if [ "$n" -ge 8 ]; then echo "pip install failed after $n attempts" >&2; exit 1; fi; \
      echo "pip install attempt $n hit a network error; retrying in 5s..." >&2; \
      sleep 5; \
    done

COPY Server/app ./app
COPY Server/curriculum_database.json ./curriculum_database.json
# Built frontend from stage 1 → served by FastAPI at "/"
COPY --from=web /web/out ./static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
