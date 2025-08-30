from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'brand', 'model', 'year', 'price_usd', 'created_at')
    list_filter = ('brand', 'year', 'body_type')
    search_fields = ('name', 'brand', 'model', 'body_type')
