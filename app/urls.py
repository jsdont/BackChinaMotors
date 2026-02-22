from django.urls import path
from .views import my_leads

urlpatterns = [
    path("my-leads/", my_leads),
]