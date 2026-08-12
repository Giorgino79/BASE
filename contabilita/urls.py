from django.urls import path
from . import views

app_name = 'contabilita'

urlpatterns = [
    path('',                              views.dashboard,        name='dashboard'),
    path('prima-nota/',                   views.prima_nota_list,  name='prima_nota_list'),
    # "Nuovo movimento" porta al selettore dell'operazione, non più
    # direttamente al form libero: quello vive un livello più sotto.
    path('prima-nota/nuovo/',             views.nuova_registrazione, name='nuova_registrazione'),
    path('prima-nota/nuovo/manuale/',     views.movimento_create, name='movimento_create'),
    path('prima-nota/documenti/',         views.documenti_suggerimenti, name='documenti_suggerimenti'),
    path('incassi/nuovo/',                views.incasso_create,         name='incasso_create'),
    path('incassi/clienti/',              views.incasso_clienti,        name='incasso_clienti'),
    path('incassi/fatture/',              views.incasso_fatture,        name='incasso_fatture'),
    path('pagamenti/nuovo/',              views.pagamento_create,       name='pagamento_create'),
    path('pagamenti/fornitori/',          views.pagamento_fornitori,    name='pagamento_fornitori'),
    path('pagamenti/fatture/',            views.pagamento_fatture,      name='pagamento_fatture'),
    path('prima-nota/<int:pk>/',          views.MovimentoDetailView.as_view(), name='movimento_detail'),
    path('prima-nota/<int:pk>/storna/',   views.movimento_storna, name='movimento_storna'),
    path('prima-nota/<int:pk>/elimina/',  views.movimento_delete, name='movimento_delete'),
    path('mastrino/<int:pk>/',            views.mastrino,         name='mastrino'),
    path('impostazioni/',                 views.impostazioni,        name='impostazioni'),
    path('conti/',                        views.conti_list,          name='conti_list'),
    path('conti/suggerimenti/',           views.conti_suggerimenti,  name='conti_suggerimenti'),
    path('conti/nuovo/',                  views.conto_create,     name='conto_create'),
    path('conti/<int:pk>/modifica/',      views.conto_edit,       name='conto_edit'),
    path('conti/<int:pk>/elimina/',       views.conto_delete,     name='conto_delete'),
]
