from django.contrib import admin
from .models import Store, Category, Product, PriceHistory


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'category', 'current_price', 'old_price', 'scraped_at']
    list_filter = ['store', 'category', 'in_stock']
    search_fields = ['name', 'brand']
    readonly_fields = ['created_at', 'scraped_at']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'price', 'recorded_at']
    list_filter = ['product__store', 'product__category']
