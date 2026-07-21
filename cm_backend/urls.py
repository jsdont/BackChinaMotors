from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views import (
    PhoneTokenObtainPairView,
    RegisterPersonView,
    RegisterCompanyView,
    RegisterServiceView,
    RegisterBankView,
    RegisterPartnerView,
    MyDealsView,
    AssignedDealsView,
    DealDetailView,
    UpdateMyAssignmentView,
    DealCommentsView,
    DealPaymentsView,
    DealDocumentsView,
    ManagerDealsView,
    ManagerDealStatusView,
    ManagerStatsView,
    ManagerDealPaymentsCreateView,
    ManagerDealDocumentsCreateView,
)
from app.webhooks import tawk_webhook, contacts_form
from cars.views import rates_view, sitemap_vehicles

urlpatterns = [
    path("admin/", admin.site.urls),

    # Referenced from the frontend's robots.txt (Sitemap: ...) since only
    # the backend knows the current catalog.
    path("sitemap-vehicles.xml", sitemap_vehicles),

    # 🔹 tawk.to webhook
    path("api/tawk/webhook/", tawk_webhook),

    path("api/", include("cars.urls")),
    path("api/contacts/", contacts_form),
    path("api/rates/", rates_view),

    path("api/auth/login/", PhoneTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/register/person/", RegisterPersonView.as_view(), name="register_person"),
    path("api/auth/register/company/", RegisterCompanyView.as_view(), name="register_company"),
    path("api/auth/register/service/", RegisterServiceView.as_view(), name="register_service"),
    path("api/auth/register/bank/", RegisterBankView.as_view(), name="register_bank"),
    path("api/auth/register/partner/", RegisterPartnerView.as_view(), name="register_partner"),

    path("api/deals/my/", MyDealsView.as_view(), name="my_deals"),
    path("api/deals/assigned/", AssignedDealsView.as_view(), name="assigned_deals"),
    path("api/deals/<int:pk>/", DealDetailView.as_view(), name="deal_detail"),
    path("api/deals/assignments/<int:pk>/", UpdateMyAssignmentView.as_view(), name="update_assignment"),
    path("api/deals/<int:deal_id>/comments/", DealCommentsView.as_view(), name="deal_comments"),
    path("api/deals/<int:deal_id>/payments/", DealPaymentsView.as_view(), name="deal_payments"),
    path("api/deals/<int:deal_id>/documents/", DealDocumentsView.as_view(), name="deal_documents"),

    # Кабинет менеджера
    path("api/manager/deals/", ManagerDealsView.as_view(), name="manager_deals"),
    path("api/manager/deals/<int:pk>/status/", ManagerDealStatusView.as_view(), name="manager_deal_status"),
    path("api/manager/deals/<int:deal_id>/payments/", ManagerDealPaymentsCreateView.as_view(), name="manager_deal_payments_create"),
    path("api/manager/deals/<int:deal_id>/documents/", ManagerDealDocumentsCreateView.as_view(), name="manager_deal_documents_create"),
    path("api/manager/stats/", ManagerStatsView.as_view(), name="manager_stats"),

    path("api/", include("app.urls")),
]
