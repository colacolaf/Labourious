# ── Stage 1: Frontend build ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --production=false

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Backend runtime ─────────────────────────────────────────────────
FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/build ./frontend/build

RUN mkdir -p data logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
