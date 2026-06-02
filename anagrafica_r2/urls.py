from django.urls import path
from . import views

app_name = 'anagrafica'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # ── Clienti (Aziende) ────────────────────────────────────────────────────
    path('clienti/',                   views.AziendaListView.as_view(),   name='azienda_list'),
    path('clienti/nuovo/',             views.AziendaCreateView.as_view(), name='azienda_create'),
    path('clienti/<int:pk>/',          views.AziendaDetailView.as_view(), name='azienda_detail'),
    path('clienti/<int:pk>/modifica/', views.AziendaUpdateView.as_view(), name='azienda_update'),
    path('clienti/<int:pk>/elimina/',  views.AziendaDeleteView.as_view(), name='azienda_delete'),

    # ── Filiali ───────────────────────────────────────────────────────────────
    path('sedi/',                                    views.FilialeGlobaleListView.as_view(), name='filiale_list'),
    path('sedi/export-csv/',                         views.export_filiali_csv,               name='export_filiali_csv'),
    path('clienti/<int:cliente_pk>/nuova-filiale/',  views.FilialeCreateView.as_view(),      name='filiale_create'),
    path('filiali/<int:pk>/',                        views.FilialeDetailView.as_view(),      name='filiale_detail'),
    path('filiali/<int:pk>/modifica/',               views.FilialeUpdateView.as_view(),      name='filiale_update'),
    path('filiali/<int:pk>/elimina/',                views.FilialeDeleteView.as_view(),      name='filiale_delete'),

    # ── Fornitori ─────────────────────────────────────────────────────────────
    path('fornitori/',                   views.FornitoreListView.as_view(),   name='fornitore_list'),
    path('fornitori/nuovo/',             views.FornitoreCreateView.as_view(), name='fornitore_create'),
    path('fornitori/export-csv/',        views.export_fornitori_csv,          name='export_fornitori_csv'),
    path('fornitori/<int:pk>/',          views.FornitoreDetailView.as_view(), name='fornitore_detail'),
    path('fornitori/<int:pk>/modifica/', views.FornitoreUpdateView.as_view(), name='fornitore_update'),
    path('fornitori/<int:pk>/elimina/',  views.FornitoreDeleteView.as_view(), name='fornitore_delete'),
    path('fornitori/<int:pk>/pdf/',      views.fornitore_pdf,                 name='fornitore_pdf'),

    # ── Privati ───────────────────────────────────────────────────────────────
    path('privati/',                   views.PrivatoListView.as_view(),   name='privato_list'),
    path('privati/nuovo/',             views.PrivatoCreateView.as_view(), name='privato_create'),
    path('privati/<int:pk>/',          views.PrivatoDetailView.as_view(), name='privato_detail'),
    path('privati/<int:pk>/modifica/', views.PrivatoUpdateView.as_view(), name='privato_update'),
    path('privati/<int:pk>/elimina/',  views.PrivatoDeleteView.as_view(), name='privato_delete'),

    # ── Utility ───────────────────────────────────────────────────────────────
    path('toggle/<str:tipo>/<int:pk>/', views.toggle_attivo, name='toggle_attivo'),
]
