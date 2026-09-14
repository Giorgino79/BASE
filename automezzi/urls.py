from django.urls import path
from .views import (
    DashboardView,
    # Automezzi
    AutomezzoListView, AutomezzoDetailView, AutomezzoCreateView,
    AutomezzoUpdateView, AutomezzoDeleteView,
    # Manutenzioni
    ManutenzioneListView, ManutenzioneDetailView, ManutenzioneCreateView,
    ManutenzioneUpdateView, ManutenzioneDeleteView,
    ManutenzioneResponsabileView, ManutenzioneFinaleView,
    AllegatoManutenzioneCreateView,
    manutenzione_prendi_carico_inline, manutenzione_completa_inline,
    # Rifornimenti
    RifornimentoListView, RifornimentoDetailView, RifornimentoCreateView,
    RifornimentoUpdateView, RifornimentoDeleteView,
    # Eventi
    EventoListView, EventoDetailView, EventoCreateView,
    EventoUpdateView, EventoDeleteView,
)

app_name = "automezzi"

urlpatterns = [
    # Dashboard
    path("", DashboardView.as_view(), name="dashboard"),

    # ── AUTOMEZZI ──────────────────────────────────────────────
    path("automezzi/", AutomezzoListView.as_view(), name="automezzo_list"),
    path("automezzi/nuovo/", AutomezzoCreateView.as_view(), name="automezzo_create"),
    path("automezzi/<int:pk>/", AutomezzoDetailView.as_view(), name="automezzo_detail"),
    path("automezzi/<int:pk>/modifica/", AutomezzoUpdateView.as_view(), name="automezzo_update"),
    path("automezzi/<int:pk>/elimina/", AutomezzoDeleteView.as_view(), name="automezzo_delete"),

    # ── MANUTENZIONI ───────────────────────────────────────────
    path("manutenzioni/", ManutenzioneListView.as_view(), name="manutenzione_list"),
    path("manutenzioni/nuova/", ManutenzioneCreateView.as_view(), name="manutenzione_create"),
    path("manutenzioni/<int:pk>/", ManutenzioneDetailView.as_view(), name="manutenzione_detail"),
    path("manutenzioni/<int:pk>/modifica/", ManutenzioneUpdateView.as_view(), name="manutenzione_update"),
    path("manutenzioni/<int:pk>/elimina/", ManutenzioneDeleteView.as_view(), name="manutenzione_delete"),
    path("manutenzioni/<int:pk>/prendi-carico/", ManutenzioneResponsabileView.as_view(), name="manutenzione_prendi_carico"),
    path("manutenzioni/<int:pk>/prendi-carico-inline/", manutenzione_prendi_carico_inline, name="manutenzione_prendi_carico_inline"),
    path("manutenzioni/<int:pk>/completa/", ManutenzioneFinaleView.as_view(), name="manutenzione_completa"),
    path("manutenzioni/<int:pk>/completa-inline/", manutenzione_completa_inline, name="manutenzione_completa_inline"),
    path("manutenzioni/<int:manutenzione_pk>/allegati/nuovo/", AllegatoManutenzioneCreateView.as_view(), name="allegato_manutenzione_create"),
    # Annidate per automezzo
    path("automezzi/<int:automezzo_pk>/manutenzioni/", ManutenzioneListView.as_view(), name="manutenzione_list_automezzo"),
    path("automezzi/<int:automezzo_pk>/manutenzioni/nuova/", ManutenzioneCreateView.as_view(), name="manutenzione_create_automezzo"),

    # ── RIFORNIMENTI ───────────────────────────────────────────
    path("rifornimenti/", RifornimentoListView.as_view(), name="rifornimento_list"),
    path("rifornimenti/nuovo/", RifornimentoCreateView.as_view(), name="rifornimento_create"),
    path("rifornimenti/<int:pk>/", RifornimentoDetailView.as_view(), name="rifornimento_detail"),
    path("rifornimenti/<int:pk>/modifica/", RifornimentoUpdateView.as_view(), name="rifornimento_update"),
    path("rifornimenti/<int:pk>/elimina/", RifornimentoDeleteView.as_view(), name="rifornimento_delete"),
    # Annidate per automezzo
    path("automezzi/<int:automezzo_pk>/rifornimenti/", RifornimentoListView.as_view(), name="rifornimento_list_automezzo"),
    path("automezzi/<int:automezzo_pk>/rifornimenti/nuovo/", RifornimentoCreateView.as_view(), name="rifornimento_create_automezzo"),

    # ── EVENTI ─────────────────────────────────────────────────
    path("eventi/", EventoListView.as_view(), name="evento_list"),
    path("eventi/nuovo/", EventoCreateView.as_view(), name="evento_create"),
    path("eventi/<int:pk>/", EventoDetailView.as_view(), name="evento_detail"),
    path("eventi/<int:pk>/modifica/", EventoUpdateView.as_view(), name="evento_update"),
    path("eventi/<int:pk>/elimina/", EventoDeleteView.as_view(), name="evento_delete"),
    # Annidate per automezzo
    path("automezzi/<int:automezzo_pk>/eventi/", EventoListView.as_view(), name="evento_list_automezzo"),
    path("automezzi/<int:automezzo_pk>/eventi/nuovo/", EventoCreateView.as_view(), name="evento_create_automezzo"),
]
