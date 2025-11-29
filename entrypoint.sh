#!/bin/sh
set -e

# Dev-friendly entrypoint: run Django's built-in server directly
python manage.py runserver 0.0.0.0:8000
