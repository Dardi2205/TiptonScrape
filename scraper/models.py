from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    url = models.URLField()
    image_url = models.URLField(blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, default='')
    model_name = models.CharField(max_length=200, blank=True, default='')
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(default=True)
    scraped_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['store', 'slug']

    def __str__(self):
        return f"{self.name} - {self.store.name}"

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.current_price:
            return round((1 - self.current_price / self.old_price) * 100)
        return 0


class PriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product.name} - {self.price} @ {self.recorded_at}"
