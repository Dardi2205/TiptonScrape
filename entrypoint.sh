#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server on port ${PORT:-8000}..."
exec gunicorn price_scraper.wsgi --bind 0.0.0.0:${PORT:-8000}
