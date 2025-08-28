from rest_framework import viewsets, permissions
from .models import Car
from .serializers import CarSerializer

class CarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Car.objects.order_by("-created_at")
    serializer_class = CarSerializer
    permission_classes = [permissions.AllowAny]
