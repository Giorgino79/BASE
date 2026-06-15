from django.urls import path
from .views import RicercaFatturazioneView, azione_fatturazione

app_name = "fatturazione_attiva"

urlpatterns = [
    path("ricerca/",  RicercaFatturazioneView.as_view(), name="ricerca"),
    path("azione/",   azione_fatturazione,               name="azione"),
]
