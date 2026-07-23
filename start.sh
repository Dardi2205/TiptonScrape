#!/bin/bash

gunicorn price_scraper.wsgi --bind 0.0.0.0:${PORT:-8000} &
GINX_PID=$!

sleep 3

python manage.py migrate --no-input 2>&1 || echo "Migrate error, continuing..."

python manage.py scrape 2>&1 || echo "Scrape error, continuing..."

python manage.py scrape --loop 2>&1 &

wait $GINX_PID
