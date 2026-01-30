from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views import PhoneTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include("cars.urls")),

    path("api/auth/login/", PhoneTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
