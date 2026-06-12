from django.urls import path
from . import views

app_name = "analysis"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("costi-servizi/", views.costi_servizi, name="costi_servizi"),
    path("api/<slug:slug>/", views.api_report, name="api_report"),
]
