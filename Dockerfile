FROM python:3.13

RUN apt-get update && apt-get install -y chromium && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/lib/playwright
ENV DJANGO_SETTINGS_MODULE=price_scraper.settings

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install chromium

COPY . .
RUN python manage.py collectstatic --noinput

CMD python manage.py migrate && gunicorn price_scraper.wsgi --bind 0.0.0.0:$PORT
