from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleViewSet, MyVehicleListingsView, MyVehicleListingDetailView

router = DefaultRouter()
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

urlpatterns = [
    # Должны идти раньше router.urls, иначе "my-listings" словится как pk
    # в /vehicles/<pk>/.
    path("vehicles/my-listings/", MyVehicleListingsView.as_view(), name="my_vehicle_listings"),
    path("vehicles/my-listings/<int:pk>/", MyVehicleListingDetailView.as_view(), name="my_vehicle_listing_detail"),
    path("", include(router.urls)),
]
