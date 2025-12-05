#!/bin/sh
set -e

# Migrate DB on start (idempotente)
python manage.py migrate --noinput

if [ "$1" = "celery" ]; then
  shift
  exec celery -A config "$@"
fi

# In production behind Nginx, use gunicorn (padrao)
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --graceful-timeout 120
