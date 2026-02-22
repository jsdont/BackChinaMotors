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