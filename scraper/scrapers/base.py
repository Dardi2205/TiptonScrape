from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from decimal import Decimal, InvalidOperation
import re
import time
import logging

logger = logging.getLogger(__name__)

# Global browser instance
_browser = None
_playwright = None


def get_browser():
    """Get or create a shared browser instance"""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        try:
            if _playwright:
                _playwright.stop()
        except Exception:
            pass
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
    return _browser


def close_browser():
    """Close the shared browser instance"""
    global _browser, _playwright
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None


def reset_browser():
    """Force reset the browser instance"""
    close_browser()


def parse_price(price_text):
    """Extract numeric price from text like '29,990 L' or '29990' or '129,00€' or '3.900,00€'"""
    if not price_text:
        return None
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[^\d.,]', '', price_text.strip())
    if not cleaned:
        return None
    
    # Handle European format with dot as thousand separator: 3.900,00 -> 3900.00
    # Pattern: digits, then groups of .digits, then ,digits
    if re.match(r'^\d{1,3}(\.\d{3})+,\d{1,2}$', cleaned):
        cleaned = cleaned.replace('.', '').replace(',', '.')
    # Handle format: 129,00 -> 129.00 (comma as decimal)
    elif ',' in cleaned and '.' not in cleaned:
        cleaned = cleaned.replace(',', '.')
    # Handle format: 1,299.00 -> 1299.00 (comma as thousand sep)
    elif ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    # Handle format: 3.900 -> 3900 (dot as thousand sep, no decimals)
    elif re.match(r'^\d{1,3}(\.\d{3})+$', cleaned):
        cleaned = cleaned.replace('.', '')
    
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def get_page(url, retries=3, wait_seconds=3, page_timeout=30000):
    """Fetch a page using Playwright (renders JavaScript)"""
    for attempt in range(retries):
        try:
            browser = get_browser()
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            })
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=page_timeout)
                time.sleep(wait_seconds)
                html = page.content()
                return html
            finally:
                page.close()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None
