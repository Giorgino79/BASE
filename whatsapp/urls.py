from django.urls import path
from . import views

app_name = "whatsapp"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("impostazioni/", views.impostazioni, name="impostazioni"),
    path("invia/", views.invia_singolo, name="invia"),
    path("broadcast/", views.broadcast_list, name="broadcast_list"),
    path("broadcast/nuovo/", views.broadcast_create, name="broadcast_create"),
    path("broadcast/<uuid:pk>/", views.broadcast_detail, name="broadcast_detail"),
    path("broadcast/<uuid:pk>/avvia/", views.broadcast_avvia, name="broadcast_avvia"),
    # API JSON
    path("api/status/", views.api_status, name="api_status"),
    path("api/disconnetti/", views.api_disconnetti, name="api_disconnetti"),
]
