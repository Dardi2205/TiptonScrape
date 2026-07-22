web: python manage.py migrate && python manage.py scrape && gunicorn price_scraper.wsgi --bind 0.0.0.0:${PORT:-8000}
