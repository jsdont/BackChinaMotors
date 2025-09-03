from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Имена из cars.views:
from cars.views import VehicleViewSet, usd_rate as rate_usd_view, telegram_hook as telegram_view

# drf-spectacular представления
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

urlpatterns = [
    path("admin/", admin.site.urls),

    # API
    path("api/", include(router.urls)),
    path("api/rate/usd/", rate_usd_view, name="rate-usd"),
    path("api/telegram", telegram_view, name="telegram"),

    # OpenAPI/Swagger:
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
