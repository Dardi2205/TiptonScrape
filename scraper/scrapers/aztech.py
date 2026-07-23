from bs4 import BeautifulSoup
from .base import get_page, parse_price
import re
import logging

logger = logging.getLogger(__name__)


class AztechScraper:
    """Scraper for aztechonline.com using Playwright"""

    STORE_NAME = 'Aztech'
    STORE_SLUG = 'aztech'
    BASE_URL = 'https://aztechonline.com'

    CATEGORY_URLS = {
        'tv': '/categorysearch?category=&term=TV',
        'pc': '/categorysearch?category=&term=laptop',
        'klima': '/categorysearch?category=&term=klima',
        'lavatrice': '/categorysearch?category=&term=lavatrice',
        'frigorifer': '/categorysearch?category=&term=frigorifer',
        'kuzhine': '/categorysearch?category=&term=kuzhine',
        'gaming': '/gaming',
    }

    OFFERS_URL = '/offers'

    def scrape_category(self, category_slug):
        url = f"{self.BASE_URL}{self.CATEGORY_URLS.get(category_slug, '')}"
        return self._scrape_url(url)

    def scrape_all_discounts(self):
        all_products = []

        # Scrape offers page
        offers_products = self._scrape_url(f"{self.BASE_URL}{self.OFFERS_URL}")
        all_products.extend(offers_products)

        # Also scrape category pages for more products
        for cat_slug, cat_url in self.CATEGORY_URLS.items():
            products = self._scrape_url(f"{self.BASE_URL}{cat_url}")
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

        # Aztech uses div.shared-product-card
        items = soup.select('.shared-product-card, [class*="product-card"]')

        for item in items:
            try:
                # Get product text
                text = item.get_text(strip=True)

                # Name
                name_el = item.select_one('h2, h3, h4, a[title], .product-title, .product-name, .product-name')
                if not name_el:
                    # Try to extract from text
                    name_match = re.search(r'^(.*?)(?:Ofertë|€)', text)
                    if name_match:
                        name = name_match.group(1).strip()
                    else:
                        continue
                else:
                    name = name_el.get('title', '') or name_el.get_text(strip=True)

                if not name or len(name) < 3:
                    continue

                # Extract prices from text
                # Aztech uses format: "€39.99€32.99" or "€349.00€249.00"
                prices = re.findall(r'€(\d+[\.,]\d+)', text)
                if len(prices) < 1:
                    # Try without euro sign
                    prices = re.findall(r'(\d+[\.,]\d+)\s*€', text)
                if len(prices) < 1:
                    continue

                # Current price is the last price (discounted)
                current_price = parse_price(prices[-1] + ' €')
                if not current_price or current_price <= 0:
                    continue

                # Old price is the first price (if higher)
                old_price = None
                if len(prices) >= 2:
                    first_price = parse_price(prices[0] + ' €')
                    if first_price and first_price > current_price:
                        old_price = first_price

                # Extract discount percentage
                discount = 0
                discount_match = re.search(r'-(\d+)%', text)
                if discount_match:
                    discount = int(discount_match.group(1))
                elif old_price and old_price > current_price:
                    discount = round((1 - current_price / old_price) * 100)

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
