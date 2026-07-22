from django.core.management.base import BaseCommand
from scraper.scrapers.gjirafa import GjirafaScraper
from scraper.scrapers.neptun import NeptunScraper
from scraper.scrapers.aztech import AztechScraper
from scraper.scrapers.base import reset_browser, close_browser
import json
import os
import logging

logger = logging.getLogger(__name__)

SCRAPERS = {
    'gjirafa': GjirafaScraper,
    'neptun': NeptunScraper,
    'aztech': AztechScraper,
}

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'cache')


class Command(BaseCommand):
    help = 'Scrape discount products and save to cache'

    def add_arguments(self, parser):
        parser.add_argument('--store', type=str, help='Scrape specific store')

    def handle(self, *args, **options):
        store_filter = options.get('store')
        os.makedirs(CACHE_DIR, exist_ok=True)

        stores = [store_filter] if store_filter else list(SCRAPERS.keys())

        for slug in stores:
            self.stdout.write(f'Scraping {slug}...', ending=' ')
            try:
                reset_browser()
                ScraperClass = SCRAPERS[slug]
                scraper = ScraperClass()
                products = scraper.scrape_all_discounts()

                for p in products:
                    p['store_name'] = scraper.STORE_NAME
                    p['store_slug'] = scraper.STORE_SLUG
                    if hasattr(p.get('current_price'), '__float__'):
                        p['current_price'] = float(p['current_price'])
                    if p.get('old_price') and hasattr(p['old_price'], '__float__'):
                        p['old_price'] = float(p['old_price'])

                cache_path = os.path.join(CACHE_DIR, f'discounts_{slug}.json')
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump({'cached_at': __import__('datetime').datetime.now().isoformat(), 'products': products}, f, ensure_ascii=False)

                self.stdout.write(self.style.SUCCESS(f'{len(products)} products'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))

        close_browser()
        self.stdout.write(self.style.SUCCESS('Done!'))
