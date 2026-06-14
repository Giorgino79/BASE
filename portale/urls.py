from django.urls import path
from . import views

app_name = 'portale'

urlpatterns = [
    path('login/',                      views.portal_login,       name='login'),
    path('logout/',                     views.portal_logout,      name='logout'),
    path('',                            views.dashboard,          name='dashboard'),
    path('bollettini/',                 views.bollettini,         name='bollettini'),
    path('bollettini/<int:pk>/pdf/',    views.bollettino_pdf,     name='bollettino_pdf'),
    path('bollettini/<int:pk>/firma/',  views.firma_bollettino,   name='firma_bollettino'),
    path('intervento/',                 views.intervento,         name='intervento'),
    path('segnalazione/',               views.segnalazione,       name='segnalazione'),
    path('calendario/',                 views.calendario,         name='calendario'),
    path('prodotti/',                   views.storico_prodotti,   name='storico_prodotti'),
    path('documenti-pmc/',              views.documenti_pmc,      name='documenti_pmc'),
    path('contratto/',                  views.contratto,          name='contratto'),
]
