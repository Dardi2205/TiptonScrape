from bs4 import BeautifulSoup
from .base import get_page, parse_price
import re
import logging

logger = logging.getLogger(__name__)


class NeptunScraper:
    """Scraper for neptun-ks.com using Playwright"""

    STORE_NAME = 'Neptun'
    STORE_SLUG = 'neptun'
    BASE_URL = 'https://www.neptun-ks.com'

    CATEGORY_URLS = {
        'tv': '/tv.nspx',
        'pc': '/laptop.nspx',
        'klima': '/kondicioner.nspx',
        'lavatrice': '/Rrobalarese.nspx',
        'frigorifer': '/frigorifere.nspx',
        'kuzhine': '/Pajisje_Kuzhine.nspx',
        'smartphone': '/smartphone.nspx',
    }

    OFFERS_URL = '/promovime.nspx'

    def scrape_category(self, category_slug):
        url = f"{self.BASE_URL}{self.CATEGORY_URLS.get(category_slug, '')}"
        return self._scrape_url(url)

    def scrape_all_discounts(self):
        all_products = []

        # Scrape TV page which has products with discounts
        tv_products = self._scrape_url(f"{self.BASE_URL}{self.CATEGORY_URLS['tv']}")
        all_products.extend(tv_products)

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

        # Neptun uses div.productWrapperInner
        items = soup.select('.productWrapperInner')

        for item in items:
            try:
                # Get product text
                text = item.get_text(strip=True)

                # Name
                name_el = item.select_one('h2, h3, h4, a[title], .product-title, .product-name')
                if not name_el:
                    # Try to extract from text - pattern: after discount badge, before "Çmimi"
                    name_match = re.search(r'(?:-\d+%|24h|E shitur)(.*?)(?:Çmimi)', text)
                    if not name_match:
                        name_match = re.search(r'^(.*?)(?:Çmimi)', text)
                    if name_match:
                        name = name_match.group(1).strip()
                    else:
                        continue
                else:
                    name = name_el.get('title', '') or name_el.get_text(strip=True)

                if not name or len(name) < 3:
                    continue

                # Extract prices from text
                # Neptun uses format: "Çmimi i rregullt179,00€haPPyçmimi129,00€12xkësti haPPy10,75€"
                # We want: old=179, current=129, ignore installment=10.75
                prices = re.findall(r'(\d+[\.,]\d+)\s*€', text)
                if len(prices) < 1:
                    continue

                # Check if there's a discount badge
                discount_match = re.search(r'-(\d+)%', text)
                
                if discount_match:
                    # Has discount: first price is old, second is current
                    discount = int(discount_match.group(1))
                    if len(prices) >= 2:
                        old_price = parse_price(prices[0] + ' €')
                        current_price = parse_price(prices[1] + ' €')
                    else:
                        current_price = parse_price(prices[0] + ' €')
                        old_price = None
                else:
                    # No discount: first price is current, ignore installments
                    current_price = parse_price(prices[0] + ' €')
                    old_price = None
                    discount = 0

                if not current_price or current_price <= 0:
                    continue

                # Validate old_price is actually higher
                if old_price and old_price <= current_price:
                    old_price = None

                # Product URL
                link_el = item.select_one('a[href]')
                product_url = ''
                if link_el:
                    product_url = link_el.get('href', '')
                    if product_url and not product_url.startswith('http'):
                        product_url = f"{self.BASE_URL}{product_url}"

                # Image
                image_url = ''
                img_el = item.select_one('img[src], img[data-src]')
                if img_el:
                    image_url = img_el.get('data-src') or img_el.get('src', '')
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
