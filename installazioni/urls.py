from django.urls import path
from . import views

app_name = "installazioni"

urlpatterns = [
    # Installazioni
    path("", views.installazione_list, name="installazione_list"),
    path("nuova/", views.installazione_create, name="installazione_create"),
    path("<int:pk>/", views.installazione_detail, name="installazione_detail"),
    path("<int:pk>/modifica/", views.installazione_update, name="installazione_update"),
    path("<int:pk>/chiudi/", views.installazione_chiudi, name="installazione_chiudi"),
    path("<int:pk>/riapri/", views.installazione_riapri, name="installazione_riapri"),
    path("<int:pk>/pdf/", views.installazione_pdf, name="installazione_pdf"),

    path("<int:pk>/galleria/", views.installazione_galleria, name="installazione_galleria"),

    # Postazioni
    path("<int:inst_pk>/postazione/nuova/", views.postazione_create, name="postazione_create"),
    path("postazione/<int:pk>/", views.postazione_detail, name="postazione_detail"),
    path("postazione/<int:pk>/modifica/", views.postazione_update, name="postazione_update"),
    path("postazione/<int:pk>/elimina/", views.postazione_delete, name="postazione_delete"),
    path("postazione/<int:pk>/qrcode/", views.postazione_qrcode, name="postazione_qrcode"),
    path("postazione/<int:pk>/pin/", views.postazione_pin, name="postazione_pin"),
    path("postazione/<int:pk>/unpin/", views.postazione_unpin, name="postazione_unpin"),

    # Planimetrie
    path("<int:inst_pk>/planimetria/nuova/", views.planimetria_create, name="planimetria_create"),
    path("planimetria/<int:pk>/", views.planimetria_detail, name="planimetria_detail"),
    path("planimetria/<int:pk>/elimina/", views.planimetria_delete, name="planimetria_delete"),

    # Interventi
    path("<int:inst_pk>/intervento/nuovo/", views.intervento_create, name="intervento_create"),
    path("intervento/<int:pk>/", views.intervento_detail, name="intervento_detail"),
    path("intervento/<int:pk>/elimina/", views.intervento_delete, name="intervento_delete"),
]
