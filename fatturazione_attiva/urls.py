from django.urls import path
from .views import (
    FatturazioneDashboardView, FattureDaIncassareView,
    fattura_sollecito, invia_sollecito,
    RicercaFatturazioneView, azione_fatturazione,
    FattureListView, FatturaDetailView,
    fattura_pdf, fattura_segna_pagata, fattura_annulla,
    emetti_nota_credito, NotaCreditoDetailView, nc_pdf,
)

app_name = "fatturazione_attiva"

urlpatterns = [
    path("",                                FatturazioneDashboardView.as_view(), name="dashboard"),
    path("da-incassare/",                   FattureDaIncassareView.as_view(),    name="da_incassare"),
    path("ricerca/",                        RicercaFatturazioneView.as_view(),   name="ricerca"),
    path("azione/",                         azione_fatturazione,                 name="azione"),
    path("fatture/",                        FattureListView.as_view(),           name="fatture_list"),
    path("fatture/<int:pk>/",              FatturaDetailView.as_view(),          name="fattura_detail"),
    path("fatture/<int:pk>/pdf/",          fattura_pdf,                          name="fattura_pdf"),
    path("fatture/<int:pk>/pagata/",       fattura_segna_pagata,                 name="fattura_pagata"),
    path("fatture/<int:pk>/annulla/",      fattura_annulla,                      name="fattura_annulla"),
    path("fatture/<int:pk>/sollecito/",    fattura_sollecito,                    name="fattura_sollecito"),
    path("fatture/<int:pk>/invia-sollecito/", invia_sollecito,                  name="invia_sollecito"),
    path("fatture/<int:pk>/nota-credito/", emetti_nota_credito,                  name="emetti_nc"),
    path("note-credito/<int:pk>/",         NotaCreditoDetailView.as_view(),      name="nc_detail"),
    path("note-credito/<int:pk>/pdf/",     nc_pdf,                               name="nc_pdf"),
]
