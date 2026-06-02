"""
ANAGRAFICA URLS - URL configuration per anagrafica
=================================================

URL patterns per la gestione anagrafica (senza rappresentanti):
- Dashboard anagrafica
- CRUD Clienti  
- CRUD Fornitori
- API e utility

NOTA: Tutti gli URL relativi ai rappresentanti sono stati rimossi
"""

from django.urls import path
from . import views

app_name = "anagrafica"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # ================== CLIENTI ==================
    path("clienti/", views.ClienteListView.as_view(), name="cliente_list"),
    path("clienti/nuovo/", views.ClienteCreateView.as_view(), name="cliente_create"),
    path(
        "clienti/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente_detail"
    ),
    path(
        "clienti/<int:pk>/modifica/",
        views.ClienteUpdateView.as_view(),
        name="cliente_update",
    ),
    path(
        "clienti/<int:pk>/elimina/",
        views.ClienteDeleteView.as_view(),
        name="cliente_delete",
    ),
    # ================== FORNITORI ==================
    path("fornitori/", views.FornitoreListView.as_view(), name="fornitore_list"),
    path(
        "fornitori/nuovo/", views.FornitoreCreateView.as_view(), name="fornitore_create"
    ),
    path(
        "fornitori/<int:pk>/",
        views.FornitoreDetailView.as_view(),
        name="fornitore_detail",
    ),
    path(
        "fornitori/<int:pk>/modifica/",
        views.FornitoreUpdateView.as_view(),
        name="fornitore_update",
    ),
    path(
        "fornitori/<int:pk>/elimina/",
        views.FornitoreDeleteView.as_view(),
        name="fornitore_delete",
    ),
    # ================== UTILITY ==================
    path("toggle/<str:tipo>/<int:pk>/", views.toggle_attivo, name="toggle_attivo"),

    # ================== PDF ==================
    path("clienti/<int:pk>/pdf/", views.cliente_pdf, name="cliente_pdf"),
    path("fornitori/<int:pk>/pdf/", views.fornitore_pdf, name="fornitore_pdf"),
    path("clienti/lista/pdf/", views.clienti_lista_pdf, name="clienti_lista_pdf"),
    path("fornitori/lista/pdf/", views.fornitori_lista_pdf, name="fornitori_lista_pdf"),

    # ================== CSV ==================
    path("clienti/export/csv/", views.export_clienti_csv, name="export_clienti_csv"),
    path("fornitori/export/csv/", views.export_fornitori_csv, name="export_fornitori_csv"),

    # ================== API ==================
    path("api/search/", views.api_search, name="api_search"),
    path("api/stats/", views.api_stats, name="api_stats"),
]
