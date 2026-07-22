from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q, Min, Max, Avg, F
from .models import Product, Store, Category, PriceHistory
from .scrapers.gjirafa import GjirafaScraper
from .scrapers.neptun import NeptunScraper
from .scrapers.aztech import AztechScraper
import json
import os
import threading
from datetime import timedelta, datetime
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
CACHE_TTL = 3600  # 1 hour in seconds

SCRAPERS = {
    'gjirafa': GjirafaScraper,
    'neptun': NeptunScraper,
    'aztech': AztechScraper,
}

STORES_INFO = [
    {'slug': 'gjirafa', 'name': 'GjirafaMall', 'url': 'https://gjirafamall.com'},
    {'slug': 'neptun', 'name': 'Neptun', 'url': 'https://www.neptun-ks.com'},
    {'slug': 'aztech', 'name': 'Aztech', 'url': 'https://aztechonline.com'},
]


def _get_cache_path(store_slug):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f'discounts_{store_slug}.json')


def _read_cache(store_slug):
    path = _get_cache_path(store_slug)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data['cached_at'])
        age = (datetime.now() - cached_at).total_seconds()
        if age < CACHE_TTL:
            return data['products']
    except Exception:
        pass
    return None


def _write_cache(store_slug, products):
    path = _get_cache_path(store_slug)
    data = {
        'cached_at': datetime.now().isoformat(),
        'products': products,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def _scrape_store(store_slug):
    try:
        from .scrapers.base import reset_browser
        reset_browser()
        ScraperClass = SCRAPERS[store_slug]
        scraper = ScraperClass()
        products = scraper.scrape_all_discounts()
        for p in products:
            p['store_name'] = scraper.STORE_NAME
            p['store_slug'] = scraper.STORE_SLUG
            # Convert Decimal to float for JSON
            if hasattr(p.get('current_price'), '__float__'):
                p['current_price'] = float(p['current_price'])
            if p.get('old_price') and hasattr(p['old_price'], '__float__'):
                p['old_price'] = float(p['old_price'])
        _write_cache(store_slug, products)
        logger.info(f"Cache updated for {store_slug}: {len(products)} products")
    except Exception as e:
        logger.error(f"Error scraping {store_slug}: {e}")


def _scrape_all_background():
    for slug in SCRAPERS:
        _scrape_store(slug)


def home(request):
    categories = Category.objects.all()
    stores = Store.objects.filter(is_active=True)

    category_filter = request.GET.get('category', '')
    store_filter = request.GET.get('store', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'name')
    view_mode = request.GET.get('view', 'grid')

    products = Product.objects.select_related('store', 'category').all()

    if category_filter:
        products = products.filter(category__slug=category_filter)
    if store_filter:
        products = products.filter(store__slug=store_filter)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query)
        )

    if sort_by == 'price_asc':
        products = products.order_by('current_price')
    elif sort_by == 'price_desc':
        products = products.order_by('-current_price')
    elif sort_by == 'discount':
        products = products.order_by('old_price')
    else:
        products = products.order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'stores': stores,
        'current_category': category_filter,
        'current_store': store_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'view_mode': view_mode,
        'total_products': products.count(),
    }
    return render(request, 'home.html', context)


def product_detail(request, product_id):
    try:
        product = Product.objects.select_related('store', 'category').get(id=product_id)
    except Product.DoesNotExist:
        return render(request, '404.html', status=404)

    price_history = PriceHistory.objects.filter(
        product=product
    ).order_by('recorded_at')[:90]

    history_data = {
        'dates': [h.recorded_at.strftime('%d %b %Y') for h in reversed(price_history)],
        'prices': [float(h.price) for h in reversed(price_history)],
    }

    similar_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id).select_related('store')[:10]

    context = {
        'product': product,
        'price_history': history_data,
        'similar_products': similar_products,
    }
    return render(request, 'product_detail.html', context)


def api_products(request):
    """API endpoint for products"""
    products = Product.objects.select_related('store', 'category').all()

    category = request.GET.get('category')
    store = request.GET.get('store')
    search = request.GET.get('q')

    if category:
        products = products.filter(category__slug=category)
    if store:
        products = products.filter(store__slug=store)
    if search:
        products = products.filter(name__icontains=search)

    data = []
    for p in products[:100]:
        data.append({
            'id': p.id,
            'name': p.name,
            'price': float(p.current_price),
            'old_price': float(p.old_price) if p.old_price else None,
            'store': p.store.name,
            'category': p.category.name if p.category else '',
            'url': p.url,
            'image_url': p.image_url,
            'discount': p.discount_percent,
        })

    return JsonResponse({'products': data})


def api_price_history(request, product_id):
    """API endpoint for price history"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    history = PriceHistory.objects.filter(
        product=product
    ).order_by('recorded_at')

    days = int(request.GET.get('days', 30))
    cutoff = timezone.now() - timedelta(days=days)
    history = history.filter(recorded_at__gte=cutoff)

    data = {
        'dates': [h.recorded_at.strftime('%Y-%m-%d') for h in history],
        'prices': [float(h.price) for h in history],
    }

    return JsonResponse(data)


def api_stats(request):
    """API endpoint for dashboard stats"""
    total_products = Product.objects.count()
    total_stores = Store.objects.filter(is_active=True).count()
    total_categories = Category.objects.count()

    price_stats = Product.objects.aggregate(
        min_price=Min('current_price'),
        max_price=Max('current_price'),
        avg_price=Avg('current_price'),
    )

    products_on_discount = Product.objects.filter(
        old_price__isnull=False,
        old_price__gt=0,
    ).count()

    return JsonResponse({
        'total_products': total_products,
        'total_stores': total_stores,
        'total_categories': total_categories,
        'min_price': float(price_stats['min_price'] or 0),
        'max_price': float(price_stats['max_price'] or 0),
        'avg_price': float(price_stats['avg_price'] or 0),
        'products_on_discount': products_on_discount,
    })


def discounts(request):
    """Scrape and display products on sale from all stores with buttons - uses cache for speed"""
    store_slug = request.GET.get('store', 'all')
    category = request.GET.get('category', '')

    products = []
    current_store_name = ''
    is_cached = False

    try:
        if store_slug and store_slug in SCRAPERS:
            # Try cache first
            cached = _read_cache(store_slug)
            if cached:
                products = cached
                is_cached = True
            else:
                # Scrape and cache
                _scrape_store(store_slug)
                products = _read_cache(store_slug) or []
            current_store_name = SCRAPERS[store_slug].STORE_NAME if store_slug in SCRAPERS else store_slug

        elif store_slug == 'all':
            # Try cache for all stores
            all_cached = []
            for slug in SCRAPERS:
                cached = _read_cache(slug)
                if cached:
                    all_cached.extend(cached)
                    is_cached = True
                else:
                    # Scrape missing store
                    _scrape_store(slug)
                    new_cached = _read_cache(slug) or []
                    all_cached.extend(new_cached)
            products = all_cached
            current_store_name = 'Te gjitha dyqanet'

        else:
            current_store_name = 'Zgjedhni dyqanin'
    except Exception as e:
        logger.error(f"Error in discounts view: {e}")

    # If we used cache, refresh in background if stale
    if is_cached:
        threading.Thread(target=_scrape_all_background, daemon=True).start()

    products.sort(key=lambda x: x.get('discount_percent', 0), reverse=True)

    context = {
        'products': products,
        'total_count': len(products),
        'current_store': store_slug,
        'current_store_name': current_store_name,
        'current_category': category,
        'stores': STORES_INFO,
        'page_title': 'Produkte ne Zbritje',
    }
    return render(request, 'discounts.html', context)
