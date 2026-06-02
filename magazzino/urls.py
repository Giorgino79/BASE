from django.urls import path
from . import views

app_name = "magazzino"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Categorie
    path("categorie/", views.CategoriaListView.as_view(), name="categoria_list"),
    path("categorie/nuova/", views.CategoriaCreateView.as_view(), name="categoria_create"),
    path("categorie/<int:pk>/modifica/", views.CategoriaUpdateView.as_view(), name="categoria_update"),

    # Prodotti
    path("prodotti/", views.ProdottoListView.as_view(), name="prodotto_list"),
    path("prodotti/nuovo/", views.ProdottoCreateView.as_view(), name="prodotto_create"),
    path("prodotti/<int:pk>/", views.ProdottoDetailView.as_view(), name="prodotto_detail"),
    path("prodotti/<int:pk>/modifica/", views.ProdottoUpdateView.as_view(), name="prodotto_update"),
    path("prodotti/<int:pk>/elimina/", views.ProdottoDeleteView.as_view(), name="prodotto_delete"),
    path("prodotti/<int:pk>/invia-scheda/", views.prodotto_invia_scheda, name="prodotto_invia_scheda"),

    # Ricezioni
    path("ricezioni/da-ordine/<int:oda_pk>/", views.ricezione_da_ordine, name="ricezione_da_ordine"),
    path("api/oda-righe/<int:oda_pk>/", views.api_oda_righe, name="api_oda_righe"),
    path("ricezioni/", views.ricezione_list, name="ricezione_list"),
    path("ricezioni/nuova/", views.RicezioneCreateView.as_view(), name="ricezione_create"),
    path("ricezioni/<int:pk>/", views.RicezioneDetailView.as_view(), name="ricezione_detail"),
    path("ricezioni/<int:pk>/modifica/", views.RicezioneUpdateView.as_view(), name="ricezione_update"),
    path("ricezioni/<int:pk>/elimina/", views.RicezioneDeleteView.as_view(), name="ricezione_delete"),

    # Scorte
    path("api/scorta-prodotto/<int:pk>/", views.api_scorta_prodotto, name="api_scorta_prodotto"),
    path("scorte/", views.scorte_dashboard, name="scorte_dashboard"),
    path("scorte/stabilimento/<int:pk>/", views.scorte_stabilimento, name="scorte_stabilimento"),
    path("scorte/stabilimento/<int:pk>/rettifica/", views.rettifica_scorta, name="rettifica_scorta"),
    path("scorte/mezzo/<int:pk>/", views.scorte_mezzo, name="scorte_mezzo"),
    path("scorte/mezzo/<int:mezzo_pk>/operazione/", views.mezzo_operazione_rapida, name="mezzo_operazione_rapida"),
    path("scorte/carico/", views.carico_mezzo_list, name="carico_mezzo_list"),
    path("scorte/carico/nuovo/", views.CaricoMezzoCreateView.as_view(), name="carico_mezzo_create"),
    path("scorte/carico/<int:pk>/", views.CaricoMezzoDetailView.as_view(), name="carico_mezzo_detail"),
    path("scorte/carico/<int:pk>/modifica/", views.CaricoMezzoUpdateView.as_view(), name="carico_mezzo_update"),
    path("scorte/carico/<int:pk>/elimina/", views.carico_mezzo_delete, name="carico_mezzo_delete"),
]
