from django.urls import path
from . import views

app_name = 'scraper'

urlpatterns = [
    path('', views.home, name='home'),
    path('zbritje/', views.discounts, name='discounts'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('api/products/', views.api_products, name='api_products'),
    path('api/price-history/<int:product_id>/', views.api_price_history, name='api_price_history'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
