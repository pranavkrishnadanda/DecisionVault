#!/usr/bin/env bash
set -e

echo "🚀 Starting DecisionVault backend..."

# Always ensure deps installed (safe + idempotent)
echo "📦 Syncing dependencies..."
uv sync

echo "📦 Running migrations..."
.venv/bin/python manage.py migrate --noinput

echo "🌐 Starting Gunicorn..."
exec .venv/bin/gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120 \
  --log-level debug \
  --access-logfile - \
  --error-logfile -
