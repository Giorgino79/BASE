from django.urls import path
from . import views

app_name = "analysis"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/<slug:slug>/", views.api_report, name="api_report"),
]
