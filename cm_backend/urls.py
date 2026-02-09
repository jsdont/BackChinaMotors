from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views import PhoneTokenObtainPairView
from app.webhooks import tawk_webhook
from app.webhooks import tawk_webhook, contacts_form

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔹 tawk.to webhook
    path("api/tawk/webhook/", tawk_webhook),

    path("api/", include("cars.urls")),
    path("api/contacts/", contacts_form),

    path("api/auth/login/", PhoneTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
