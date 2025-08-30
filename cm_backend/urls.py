from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from rest_framework.routers import DefaultRouter
from cars.views import CarViewSet

from cm_backend.views import telegram_hook, usd_rate

router = DefaultRouter()
router.register(r"cars", CarViewSet, basename="car")

def health(request):
    return JsonResponse({"status": "ok", "service": "china-motors-backend"}, status=200)

urlpatterns = [
    path("", health, name="healthz"),
    path("admin/", admin.site.urls),

    # API
    path("api/", include(router.urls)),
    path("api/telegram", telegram_hook),  # POST
    path("api/rate/usd", usd_rate),       # GET
]

# Swagger / ReDoc (если используешь drf-spectacular)
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cars.views import VehicleViewSet

router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet, basename='vehicle')

urlpatterns = [
    path('api/', include(router.urls)),
    # ... твои остальные api-маршруты ...
]
