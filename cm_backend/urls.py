from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cars.views import VehicleViewSet, usd_rate, telegram_hook  # <-- Имена как во views.py

router = DefaultRouter()
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

from django.http import HttpResponse
def health(request): return HttpResponse("ok")

urlpatterns = [
    path("admin/", admin.site.urls),

    # API
    path("api/", include(router.urls)),
    path("api/rate/usd/", usd_rate, name="rate-usd"),
    path("api/telegram", telegram_hook, name="telegram"),
    path("healthz/", health),


    # Swagger/OpenAPI (если нужен — см. пункт 2)
    # path("api/schema/", include("drf_spectacular.urls")),
    # path("api/schema/swagger-ui/", include("drf_spectacular.urls", namespace="schema")),
]
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
