from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'category', 'availability')
    list_filter = ('category', 'availability')
    search_fields = ('id', 'title')
