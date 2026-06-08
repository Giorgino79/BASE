from django.urls import path
from . import views

app_name = "servizi"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tecnico/", views.dashboard_tecnico, name="dashboard_tecnico"),

    # Servizi
    path("servizi/",                   views.ServizioListView.as_view(),   name="servizio_list"),
    path("servizi/nuovo/",             views.ServizioCreateView.as_view(), name="servizio_create"),
    path("servizi/<int:pk>/",          views.ServizioDetailView.as_view(), name="servizio_detail"),
    path("servizi/<int:pk>/modifica/", views.ServizioUpdateView.as_view(), name="servizio_update"),
    path("servizi/<int:pk>/elimina/",  views.ServizioDeleteView.as_view(), name="servizio_delete"),

    # Contratti
    path("contratti/",                              views.ContrattoListView.as_view(),   name="contratto_list"),
    path("contratti/nuovo/",                        views.ContrattoCreateView.as_view(), name="contratto_create"),
    path("contratti/<int:pk>/",                     views.ContrattoDetailView.as_view(), name="contratto_detail"),
    path("contratti/<int:pk>/modifica/",            views.ContrattoUpdateView.as_view(), name="contratto_update"),
    path("contratti/<int:pk>/elimina/",             views.ContrattoDeleteView.as_view(), name="contratto_delete"),
    path("contratti/filiale/<int:cf_pk>/gestisci/", views.contratto_filiale_gestisci,    name="contratto_filiale_gestisci"),
    path("contratti/<int:pk>/pdf/",                 views.contratto_pdf,                 name="contratto_pdf"),

    # ODS
    path("ods/",                   views.ODSListView.as_view(),   name="ods_list"),
    path("ods/nuovo/",             views.ODSCreateView.as_view(), name="ods_create"),
    path("ods/<int:pk>/",          views.ODSDetailView.as_view(), name="ods_detail"),
    path("ods/<int:pk>/modifica/", views.ODSUpdateView.as_view(), name="ods_update"),
    path("ods/organizzazione-giri/",    views.organizzazione_giri,     name="organizzazione_giri"),
    path("ods/<int:pk>/assegna/",        views.ods_assegna_tecnico,     name="ods_assegna_tecnico"),
    path("ods/<int:pk>/personale/",      views.ods_cambia_personale,    name="ods_cambia_personale"),
    path("ods/<int:pk>/stato/",         views.ods_set_stato,           name="ods_set_stato"),
    path("ods/<int:pk>/incassato/",     views.ods_segna_incassato,     name="ods_segna_incassato"),
    path("ods/<int:pk>/set-importo/",   views.ods_set_importo,         name="ods_set_importo"),
    path("ods/da-incassare/",           views.ods_da_incassare,        name="ods_da_incassare"),

    # Distinte
    path("distinte/",                           views.DistintaListView.as_view(), name="distinta_list"),
    path("distinte/<int:pk>/",                  views.DistintaDetailView.as_view(), name="distinta_detail"),
    path("distinte/crea/<int:tecnico_pk>/",     views.crea_distinta,               name="crea_distinta"),
    path("distinte/<int:pk>/chiudi/",            views.distinta_chiudi,             name="distinta_chiudi"),
    path("distinte/<int:pk>/chiudi-ufficio/",   views.chiudi_distinta_ufficio,     name="chiudi_distinta_ufficio"),
    path("distinte/incassi/",                   views.situazione_incassi,          name="situazione_incassi"),
    path("ods/<int:ods_pk>/chiudi-servizio/",   views.chiudi_servizio_distinta,    name="chiudi_servizio_distinta"),
    path("ods/<int:ods_pk>/aggiungi-consumo/",  views.aggiungi_consumo,            name="aggiungi_consumo"),
    path("consumo/<int:consumo_pk>/elimina/",   views.elimina_consumo,             name="elimina_consumo"),

    # Condomini ODS
    path("condomini/",                    views.condominio_list,   name="condominio_list"),
    path("condomini/nuovo/",              views.condominio_create, name="condominio_create"),
    path("condomini/<int:pk>/",           views.condominio_detail, name="condominio_detail"),
    path("condomini/<int:pk>/modifica/",  views.condominio_update, name="condominio_update"),
    path("condomini/<int:pk>/assegna/",   views.condominio_assegna_tecnico, name="condominio_assegna_tecnico"),
    path("condomini/<int:pk>/esegui/",    views.condominio_esegui,     name="condominio_esegui"),
    path("condomini/<int:pk>/pdf/",       views.condominio_pdf,        name="condominio_pdf"),
    path("condomini/<int:pk>/salva-riga/", views.condominio_salva_riga, name="condominio_salva_riga"),

    # API
    path("api/prezzo-contratto/", views.api_prezzo_contratto, name="api_prezzo_contratto"),
]
