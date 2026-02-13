from django.contrib import admin
from django.db.models import Count, Sum
from catalog.models import Product
from django.db import models


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "price",
        "availability",
        "deals_count",
        "total_profit",
    )

    list_filter = ("category", "availability")
    search_fields = ("id", "title")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            deals_count_annotated=Count(
                "leads",
                filter=models.Q(leads__status="won")
            ),
            total_profit_annotated=Sum(
                "leads__product__profit",
                filter=models.Q(leads__status="won")
            )
        )

    def deals_count(self, obj):
        return obj.deals_count_annotated or 0

    def total_profit(self, obj):
        return obj.total_profit_annotated or 0

    deals_count.short_description = "Deals"
    total_profit.short_description = "Total Profit (₸)"
