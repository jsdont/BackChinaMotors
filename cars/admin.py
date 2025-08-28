from django.contrib import admin
from .models import Car

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "name", "year", "price", "created_at")
    list_filter = ("brand", "year")
    search_fields = ("name", "brand")
