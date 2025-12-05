#!/bin/sh
set -e

# Migrate DB on start (idempotente)
python manage.py migrate --noinput

# In production behind Nginx, use gunicorn
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --graceful-timeout 120
