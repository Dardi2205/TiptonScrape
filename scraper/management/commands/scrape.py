from django.core.management.base import BaseCommand
from django.utils.text import slugify
from scraper.models import Store, Category, Product, PriceHistory
from scraper.scrapers.gjirafa import GjirafaScraper
from scraper.scrapers.neptun import NeptunScraper
from scraper.scrapers.aztech import AztechScraper
from scraper.scrapers.midea import MideaScraper
import logging

logger = logging.getLogger(__name__)

SCRAPERS = {
    'gjirafa': GjirafaScraper,
    'neptun': NeptunScraper,
    'aztech': AztechScraper,
    'midea': MideaScraper,
}

CATEGORIES = [
    ('klima', 'Klima'),
    ('tv', 'Televizor'),
    ('pc', 'Kompjuter'),
    ('lavatrice', 'Lavatrice'),
    ('frigorifer', 'Frigorifer'),
    ('kuzhine', 'Kuzhine'),
]


class Command(BaseCommand):
    help = 'Scrape products from Albanian tech stores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            help='Scrape specific store (gjirafa, neptun, aztech, midea)',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Scrape specific category (klima, tv, pc, lavatrice, frigorifer, kuzhine)',
        )

    def handle(self, *args, **options):
        store_filter = options.get('store')
        category_filter = options.get('category')

        stores_to_scrape = []
        if store_filter:
            if store_filter in SCRAPERS:
                stores_to_scrape = [store_filter]
            else:
                self.stderr.write(self.style.ERROR(f'Unknown store: {store_filter}'))
                return
        else:
            stores_to_scrape = list(SCRAPERS.keys())

        categories_to_scrape = []
        if category_filter:
            categories_to_scrape = [category_filter]
        else:
            categories_to_scrape = [c[0] for c in CATEGORIES]

        for store_slug in stores_to_scrape:
            scraper_class = SCRAPERS[store_slug]
            scraper = scraper_class()

            store, _ = Store.objects.get_or_create(
                slug=store_slug,
                defaults={
                    'name': scraper.STORE_NAME,
                    'base_url': scraper.BASE_URL,
                }
            )

            self.stdout.write(f'\nScraping {scraper.STORE_NAME}...')

            for cat_slug in categories_to_scrape:
                category, _ = Category.objects.get_or_create(
                    slug=cat_slug,
                    defaults={'name': dict(CATEGORIES).get(cat_slug, cat_slug)}
                )

                self.stdout.write(f'  Category: {category.name}...', ending=' ')

                try:
                    products = scraper.scrape_category(cat_slug)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error: {e}'))
                    continue

                count = 0
                for pdata in products:
                    product, created = Product.objects.update_or_create(
                        store=store,
                        slug=pdata['slug'],
                        defaults={
                            'name': pdata['name'],
                            'category': category,
                            'url': pdata['url'],
                            'image_url': pdata.get('image_url', ''),
                            'brand': pdata.get('brand', ''),
                            'model_name': pdata.get('model_name', ''),
                            'current_price': pdata['current_price'],
                            'old_price': pdata.get('old_price'),
                            'in_stock': pdata.get('in_stock', True),
                        }
                    )

                    PriceHistory.objects.create(
                        product=product,
                        price=pdata['current_price'],
                    )

                    count += 1

                self.stdout.write(self.style.SUCCESS(f'{count} products'))

        self.stdout.write(self.style.SUCCESS('\nScraping complete!'))
