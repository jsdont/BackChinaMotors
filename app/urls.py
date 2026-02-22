from django.urls import path
from .views import my_leads
from .views import update_lead_status

urlpatterns = [
    path("my-leads/", my_leads),
    path("leads/<int:pk>/update-status/", update_lead_status),
]