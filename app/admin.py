from django.contrib import admin
from .models import CalculatorLead

@admin.register(CalculatorLead)
class CalculatorLeadAdmin(admin.ModelAdmin):
    list_display = (
        "calc_id",
        "name",
        "phone",
        "source",
        "created_at",
    )
    list_filter = ("source", "created_at")
    search_fields = ("calc_id", "name", "phone", "message")
    ordering = ("-created_at",)
