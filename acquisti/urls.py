from django.urls import path
from . import views

app_name = "acquisti"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # ODA
    path("ordini/", views.OrdineListView.as_view(), name="ordine_list"),
    path("ordini/nuovo/", views.OrdineCreateView.as_view(), name="ordine_create"),
    path("ordini/<int:pk>/", views.OrdineDetailView.as_view(), name="ordine_detail"),
    path("ordini/<int:pk>/modifica/", views.OrdineUpdateView.as_view(), name="ordine_update"),
    path("ordini/<int:pk>/elimina/", views.OrdineDeleteView.as_view(), name="ordine_delete"),
    path("ordini/<int:pk>/stato/", views.ordine_set_stato, name="ordine_set_stato"),
    path("ordini/<int:pk>/pdf/", views.ordine_pdf, name="ordine_pdf"),
    path("ordini/<int:pk>/reinvia-mail/", views.ordine_reinvia_mail, name="ordine_reinvia_mail"),

    # Fatture passive
    path("fatture/", views.FatturaListView.as_view(), name="fattura_list"),
    path("fatture/nuova/", views.FatturaCreateView.as_view(), name="fattura_create"),
    path("fatture/<int:pk>/", views.FatturaDetailView.as_view(), name="fattura_detail"),
    path("fatture/<int:pk>/modifica/", views.FatturaUpdateView.as_view(), name="fattura_update"),
    path("fatture/<int:pk>/elimina/", views.FatturaDeleteView.as_view(), name="fattura_delete"),

    # Autofatturazione
    path("autofatturazione/", views.autofatturazione, name="autofatturazione"),
]
