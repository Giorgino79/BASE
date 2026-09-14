# 'analysis' resta un'app Django a sé (nome/namespace/gating invariati —
# "attivare solo su richiesta del cliente", stesso trattamento di
# multi_company), ma il codice reale ora vive in core/ (views_analysis.py,
# reports_analysis/, templates/core/analysis/) — vedi memoria "CORE
# definition", 27/08/2026. Questo file resta solo il collegamento URL.

from django.urls import path
from core import views_analysis as views

app_name = "analysis"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("costi-servizi/", views.costi_servizi, name="costi_servizi"),
    path("api/<slug:slug>/", views.api_report, name="api_report"),
]
