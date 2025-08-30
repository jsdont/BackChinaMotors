# cars/views.py
from rest_framework import viewsets, filters
from .models import Vehicle
from .serializers import VehicleSerializer

class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'brand', 'body_type']
