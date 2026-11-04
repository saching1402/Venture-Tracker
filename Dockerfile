# Venture GP Atlas — single Railway service: React frontend built into the Django backend.
# Connect the repo on the Railway canvas; no Root Directory needed.

# ── Stage 1: build the React app ──────────────────────────────────────────────
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# API is same-origin (/api/v1); set VITE_API_URL only for a separately hosted frontend
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ── Stage 2: Django API + the built app ───────────────────────────────────────
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=atlas.settings.production
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=web /web/dist ./frontend_dist
RUN python manage.py collectstatic --noinput

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "/app/start.sh"]
