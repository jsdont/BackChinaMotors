from rest_framework import serializers
from .models import CalculatorLead


class LeadSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)

    class Meta:
        model = CalculatorLead
        fields = [
            "id",
            "calc_id",
            "name",
            "phone",
            "status",
            "product_title",
            "profit_snapshot",
            "created_at",
            "closed_at",
        ]
class LeadStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatorLead
        fields = ["status"]


class ManagerLeadSerializer(serializers.ModelSerializer):
    """Заявка для инбокса менеджера — с текстом обращения и источником,
    чтобы можно было триажить входящие с сайта."""
    product_title = serializers.CharField(source="product.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CalculatorLead
        fields = [
            "id",
            "calc_id",
            "source",
            "name",
            "phone",
            "message",
            "page_url",
            "status",
            "status_display",
            "product_title",
            "converted_deal",
            "created_at",
            "closed_at",
        ]
        read_only_fields = fields