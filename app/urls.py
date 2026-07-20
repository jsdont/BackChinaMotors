from django.urls import path
from .views import my_leads
from .views import update_lead_status
from .views import manager_leads

urlpatterns = [
    path("my-leads/", my_leads),
    path("manager/leads/", manager_leads),
    path("leads/<int:pk>/update-status/", update_lead_status),
]