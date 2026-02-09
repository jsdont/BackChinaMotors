from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from .models import Vehicle
from .serializers import VehicleSerializer


class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vehicle.objects.all().order_by("-id")
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["brand", "model", "year", "body_type"]
    ordering_fields = ["price_usd", "year", "id"]
