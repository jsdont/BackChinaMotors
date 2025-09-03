# cars/admin.py
from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "model", "year", "price_usd")
    search_fields = ("brand", "model")
    list_per_page = 50
