from django.urls import path
from . import views

app_name = 'contabilita'

urlpatterns = [
    path('',                              views.dashboard,        name='dashboard'),
    path('prima-nota/',                   views.prima_nota_list,  name='prima_nota_list'),
    path('prima-nota/nuovo/',             views.movimento_create, name='movimento_create'),
    path('prima-nota/documenti/',         views.documenti_suggerimenti, name='documenti_suggerimenti'),
    path('incassi/nuovo/',                views.incasso_create,         name='incasso_create'),
    path('prima-nota/<int:pk>/',          views.MovimentoDetailView.as_view(), name='movimento_detail'),
    path('prima-nota/<int:pk>/elimina/',  views.movimento_delete, name='movimento_delete'),
    path('mastrino/<int:pk>/',            views.mastrino,         name='mastrino'),
    path('conti/',                        views.conti_list,          name='conti_list'),
    path('conti/suggerimenti/',           views.conti_suggerimenti,  name='conti_suggerimenti'),
    path('conti/nuovo/',                  views.conto_create,     name='conto_create'),
    path('conti/<int:pk>/modifica/',      views.conto_edit,       name='conto_edit'),
    path('conti/<int:pk>/elimina/',       views.conto_delete,     name='conto_delete'),
]
