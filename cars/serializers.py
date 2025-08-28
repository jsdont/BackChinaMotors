from rest_framework import serializers
from .models import Car

class CarSerializer(serializers.ModelSerializer):
    card_image = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ["id", "name", "brand", "price", "year",
                  "image", "card_image", "hero_image", "created_at"]

    def get_card_image(self, obj): return obj.card_url(480, 320)
    def get_hero_image(self, obj): return obj.hero_url(1600, 630)
