from bs4 import BeautifulSoup
from .base import get_page, parse_price
import re
import logging

logger = logging.getLogger(__name__)


class GjirafaScraper:
    """Scraper for gjirafamall.com using Playwright"""

    STORE_NAME = 'GjirafaMall'
    STORE_SLUG = 'gjirafa'
    BASE_URL = 'https://gjirafamall.com'

    CATEGORY_URLS = {
        'tv': '/tv-audio-foto',
        'pc': '/kompjuter-laptop-server',
        'klima': '/ngrohje-ventilim-hidraulike-shtepi',
        'lavatrice': '/rrobalarese',
        'frigorifer': '/frigorifer',
        'kuzhine': '/kuzhine',
        'celular': '/celular-tablet-navigim',
    }

    def scrape_category(self, category_slug):
        url = f"{self.BASE_URL}{self.CATEGORY_URLS.get(category_slug, '/teknologji')}"
        return self._scrape_url(url)

    def scrape_all_discounts(self):
        all_products = []
        # Only scrape main technology page for speed
        url = f"{self.BASE_URL}/teknologji"
        products = self._scrape_url(url)
        all_products.extend(products)

        seen = set()
        unique = []
        for p in all_products:
            if p['slug'] not in seen:
                seen.add(p['slug'])
                if p.get('old_price') and p['old_price'] > p['current_price']:
                    unique.append(p)
        return unique

    def _scrape_url(self, url):
        html = get_page(url, wait_seconds=5)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        products = []

        # GjirafaMall uses div.product-item for product cards
        items = soup.select('.product-item, [class*="product-item"]')

        for item in items:
            try:
                # Get product text
                text = item.get_text(strip=True)

                # Name - extract from text: "Basics from GjirafaMallProduct Name99.50 €..."
                name = ''
                # Try specific elements first
                name_el = item.select_one('h2, h3, h4, .product-title, .product-name')
                if name_el:
                    name = name_el.get_text(strip=True)
                
                # If no name found, extract from full text
                if not name or len(name) < 3:
                    # Remove "Basics from GjirafaMall" prefix, then extract name before price
                    cleaned = re.sub(r'^Basics from GjirafaMall', '', text)
                    name_match = re.match(r'^(.+?)(?:\d+[\.,]\d+\s*€)', cleaned)
                    if name_match:
                        name = name_match.group(1).strip()
                
                if not name or len(name) < 3:
                    continue

                # Extract prices from text using regex
                # Match numbers with dots/commas before € symbol
                prices = re.findall(r'(\d[\d.,]*)\s*€', text)
                if len(prices) < 1:
                    continue

                # Current price is the first price
                current_price = parse_price(prices[0] + ' €')
                if not current_price or current_price <= 0:
                    continue

                # Old price is the second price (if exists and is higher)
                old_price = None
                if len(prices) >= 2:
                    old_price = parse_price(prices[1] + ' €')
                    if old_price and old_price <= current_price:
                        old_price = None

                # Extract discount percentage
                discount = 0
                discount_match = re.search(r'-(\d+)%', text)
                if discount_match:
                    discount = int(discount_match.group(1))

                # Product URL
                link_el = item.select_one('a[href]')
                product_url = ''
                if link_el:
                    product_url = link_el.get('href', '')
                    if product_url and not product_url.startswith('http'):
                        product_url = f"{self.BASE_URL}{product_url}"

                # Image
                image_url = ''
                img_el = item.select_one('img[src], img[data-src], img[data-lazy]')
                if img_el:
                    image_url = (
                        img_el.get('data-lazy') or
                        img_el.get('data-src') or
                        img_el.get('src', '')
                    )
                    if image_url and not image_url.startswith('http'):
                        image_url = f"{self.BASE_URL}{image_url}"
                    # Fix double ? in URL: ?width=196?quality=80 -> ?width=196&quality=80
                    if '?' in image_url:
                        parts = image_url.split('?')
                        if len(parts) > 2:
                            image_url = parts[0] + '?' + '&'.join(parts[1:])

                slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip())[:500]
                if not slug:
                    continue

                products.append({
                    'name': name,
                    'slug': slug,
                    'url': product_url,
                    'image_url': image_url,
                    'current_price': current_price,
                    'old_price': old_price,
                    'brand': '',
                    'model_name': '',
                    'in_stock': True,
                    'discount_percent': discount,
                })
            except Exception as e:
                logger.debug(f"Error parsing item: {e}")
                continue

        return products
