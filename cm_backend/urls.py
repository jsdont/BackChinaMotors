from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from cars.views import VehicleViewSet, rate_usd, telegram_message

router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet, basename='vehicle')

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI схема и Swagger (удобно смотреть API)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),

    # REST
    path('api/', include(router.urls)),

    # Служебные ручки для фронта
    path('api/rate/usd', rate_usd),
    path('api/telegram', telegram_message),
]
