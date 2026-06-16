from django.urls import path
from .views import (
    RicercaFatturazioneView, azione_fatturazione,
    FattureListView, FatturaDetailView,
    fattura_pdf, fattura_segna_pagata, fattura_annulla,
)

app_name = "fatturazione_attiva"

urlpatterns = [
    path("ricerca/",                   RicercaFatturazioneView.as_view(), name="ricerca"),
    path("azione/",                    azione_fatturazione,               name="azione"),
    path("fatture/",                   FattureListView.as_view(),         name="fatture_list"),
    path("fatture/<int:pk>/",          FatturaDetailView.as_view(),       name="fattura_detail"),
    path("fatture/<int:pk>/pdf/",      fattura_pdf,                       name="fattura_pdf"),
    path("fatture/<int:pk>/pagata/",   fattura_segna_pagata,              name="fattura_pagata"),
    path("fatture/<int:pk>/annulla/",  fattura_annulla,                   name="fattura_annulla"),
]
