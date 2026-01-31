from rest_framework import viewsets, filters
from .models import Vehicle
from .serializers import VehicleSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all().order_by("-id")
    serializer_class = VehicleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["brand", "model", "year", "body_type"]
    ordering_fields = ["price_usd", "year", "id"]
    permission_classes = [IsAuthenticated]
