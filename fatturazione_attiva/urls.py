from django.urls import path
from .views import RicercaFatturazioneView

app_name = "fatturazione_attiva"

urlpatterns = [
    path("ricerca/", RicercaFatturazioneView.as_view(), name="ricerca"),
]
