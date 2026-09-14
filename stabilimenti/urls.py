from django.urls import path
from .views import (
    DashboardView,
    # Stabilimenti
    stabilimento_list, stabilimento_create, stabilimento_detail,
    stabilimento_update, toggle_attivo_stabilimento,
    # Costi
    costo_list, costo_create, costo_detail, costo_update,
    # Utenze
    utenza_create, utenza_update,
    # Documenti
    documento_list, documento_create,
    # Scadenze
    scadenze_dashboard,
)

app_name = "stabilimenti"

urlpatterns = [
    # Dashboard
    path("", DashboardView.as_view(), name="dashboard"),

    # ── STABILIMENTI ───────────────────────────────────────────
    path("stabilimenti/", stabilimento_list, name="stabilimento_list"),
    path("stabilimenti/nuovo/", stabilimento_create, name="stabilimento_create"),
    path("stabilimenti/<int:pk>/", stabilimento_detail, name="stabilimento_detail"),
    path("stabilimenti/<int:pk>/modifica/", stabilimento_update, name="stabilimento_update"),
    path("stabilimenti/<int:pk>/toggle-attivo/", toggle_attivo_stabilimento, name="stabilimento_toggle_attivo"),

    # ── COSTI ──────────────────────────────────────────────────
    path("costi/", costo_list, name="costo_list"),
    path("stabilimenti/<int:stabilimento_pk>/costi/nuovo/", costo_create, name="costo_create"),
    path("costi/<int:pk>/", costo_detail, name="costo_detail"),
    path("costi/<int:pk>/modifica/", costo_update, name="costo_update"),

    # ── UTENZE ─────────────────────────────────────────────────
    path("stabilimenti/<int:stabilimento_pk>/utenze/nuova/", utenza_create, name="utenza_create"),
    path("utenze/<int:pk>/modifica/", utenza_update, name="utenza_update"),

    # ── DOCUMENTI ──────────────────────────────────────────────
    path("stabilimenti/<int:stabilimento_pk>/documenti/", documento_list, name="documento_list"),
    path("stabilimenti/<int:stabilimento_pk>/documenti/nuovo/", documento_create, name="documento_create"),

    # ── SCADENZE ───────────────────────────────────────────────
    path("scadenze/", scadenze_dashboard, name="scadenze"),
]
