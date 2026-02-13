from django.contrib import admin
from django.utils.html import format_html
from django.db.models.functions import TruncDate
from django.db.models import Count, Sum
from django.utils import timezone

from .models import CalculatorLead



@admin.register(CalculatorLead)
class CalculatorLeadAdmin(admin.ModelAdmin):
    list_display = (
        "calc_id",
        "name",
        "phone",
        "source",
        "colored_status",
        "created_at",
        "product_link",
        "manager",
        "profit_snapshot",

    )
    
    list_filter = ("source", "status", "product", "created_at")
    search_fields = ("calc_id", "name", "phone", "message")
    ordering = ("-created_at",)

    def colored_status(self, obj):
        colors = {
            "new": "red",
            "in_progress": "orange",
            "won": "green",
            "lost": "gray",
            "contacted": "orange",
            "closed": "gray",
        }

        return format_html(
            '<b style="color:{};">{}</b>',
            colors.get(obj.status, "black"),
            obj.get_status_display()
        )

    
    colored_status.short_description = "Status"

    def product_link(self, obj):
        if obj.product:
            return format_html(
                '<a href="/admin/catalog/product/{}/change/">{}</a>',
                obj.product.id,
                obj.product.title
            )
        return "-"
    product_link.short_description = "Product"

    actions = ["mark_as_in_progress", "mark_as_won", "mark_as_lost"]

    def mark_as_in_progress(self, request, queryset):
        for obj in queryset:
            obj.status = "in_progress"
            obj.full_clean()
            obj.save()
    
    def mark_as_won(self, request, queryset):
        for obj in queryset:
            obj.status = "won"
            obj.full_clean()
            obj.save()

    def mark_as_lost(self, request, queryset):
        for obj in queryset:
            obj.status = "lost"
            obj.full_clean()
            obj.save()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        queryset = CalculatorLead.objects.all()

        total_leads = queryset.count()
        deals = queryset.filter(status="won", product__isnull=False, closed_at__isnull=False)

        total_deals = deals.count()

        total_revenue = deals.aggregate(
            total=Sum("profit_snapshot")
        )["total"] or 0


        conversion = 0
        if total_leads > 0:
            conversion = round((total_deals / total_leads) * 100, 1)

        avg_profit = 0
        if total_deals > 0:
            avg_profit = round(total_revenue / total_deals, 2)

        extra_context["crm_stats"] = {
            "total_leads": total_leads,
            "total_deals": total_deals,
            "total_revenue": total_revenue,
            "conversion": conversion,
            "avg_profit": avg_profit,
        }

        from django.db.models import Sum

        revenue_by_day = (
            deals
            .annotate(day=TruncDate("closed_at"))
            .values("day")
            .annotate(total=Sum("profit_snapshot"))
            .order_by("day")
        )

        extra_context["revenue_chart"] = [
            {
                "day": item["day"].strftime("%Y-%m-%d"),
                "total": float(item["total"] or 0),
            }
            for item in revenue_by_day
        ]

        top_products = (
            deals
            .values("product__title")
            .annotate(
                total_deals=Count("id"),
                total_profit=Sum("profit_snapshot")
            )
            .order_by("-total_profit")[:5]
        )

        extra_context["top_products"] = top_products

        # 🔥 ТОП МЕНЕДЖЕРОВ
        top_managers = (
            deals
            .values("manager__phone")
            .annotate(
                total_deals=Count("id"),
                total_profit=Sum("profit_snapshot")
            )
            .order_by("-total_profit")[:5]
        )

        extra_context["top_managers"] = top_managers


        new_count = queryset.filter(status="new").count()
        progress_count = queryset.filter(status="in_progress").count()
        won_count = queryset.filter(status="won").count()
        lost_count = queryset.filter(status="lost").count()

        extra_context["funnel"] = {
            "new": new_count,
            "in_progress": progress_count,
            "won": won_count,
            "lost": lost_count,
        }

        manager_stats = (
            deals
            .values("manager__phone")
            .annotate(
                total_deals=Count("id"),
                total_profit=Sum("profit_snapshot")
            )
            .order_by("-total_profit")
        )

        extra_context["manager_stats"] = manager_stats

        return super().changelist_view(request, extra_context=extra_context)
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(manager=request.user)
    
    def save_model(self, request, obj, form, change):
        if not obj.manager:
            obj.manager = request.user
        super().save_model(request, obj, form, change)


