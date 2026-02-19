# Stage 1: Build frontend assets
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build backend dependencies
FROM python:3.12-slim AS backend-build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN pip install --no-cache-dir uv && \
    cd backend && uv sync --frozen
COPY backend/ ./backend/

# Stage 3: Runtime
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=backend-build /app/backend /app/backend
COPY --from=backend-build /app/backend/.venv /app/backend/.venv
COPY --from=frontend-build /frontend/.next /app/frontend-build/.next
COPY --from=frontend-build /frontend/public /app/frontend-build/public

ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["gunicorn", "--chdir", "/app/backend", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
