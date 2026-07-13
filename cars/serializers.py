from rest_framework import serializers
from .models import Vehicle


OWNER_ROLE_LABELS = {
    "CUSTOMER_PERSON": "физ. лица",
    "CUSTOMER_COMPANY": "юр. лица",
}


class VehicleSerializer(serializers.ModelSerializer):
    # Для бейджа "Объявление от..." на карточке в каталоге — публичный
    # каталог не должен палить телефон/детали автора, только тип.
    is_user_listing = serializers.SerializerMethodField()
    owner_role_label = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = "__all__"

    def get_is_user_listing(self, obj):
        return obj.owner_id is not None

    def get_owner_role_label(self, obj):
        if not obj.owner_id:
            return None
        return OWNER_ROLE_LABELS.get(obj.owner.role, "клиента")


class MyVehicleListingSerializer(serializers.ModelSerializer):
    # Поля, которые реально может задать клиент, размещая своё
    # объявление — без availability/is_approved и прочих полей,
    # которыми управляет только админ.
    class Meta:
        model = Vehicle
        fields = [
            "id", "brand", "model", "year", "body_type", "category", "city",
            "extra_info", "weight_t", "wheel_formula", "gearbox",
            "engine_power_hp", "load_capacity_t", "price_kzt",
            "mileage_km", "image_url", "images", "is_approved", "created_at",
        ]
        read_only_fields = ["id", "is_approved", "created_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["owner"] = user
        validated_data["is_approved"] = False
        validated_data.setdefault("availability", "in_stock")
        return super().create(validated_data)
