"""
WSGI config for price_scraper project.
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper.settings')

application = get_wsgi_application()
