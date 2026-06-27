from django.urls import path
from . import views

app_name = "installazioni"

urlpatterns = [
    # Installazioni
    path("", views.installazione_list, name="installazione_list"),
    path("nuova/", views.installazione_create, name="installazione_create"),
    path("<int:pk>/", views.installazione_detail, name="installazione_detail"),
    path("<int:pk>/modifica/", views.installazione_update, name="installazione_update"),

    path("<int:pk>/galleria/", views.installazione_galleria, name="installazione_galleria"),

    # Postazioni
    path("<int:inst_pk>/postazione/nuova/", views.postazione_create, name="postazione_create"),
    path("postazione/<int:pk>/", views.postazione_detail, name="postazione_detail"),
    path("postazione/<int:pk>/modifica/", views.postazione_update, name="postazione_update"),
    path("postazione/<int:pk>/elimina/", views.postazione_delete, name="postazione_delete"),
    path("postazione/<int:pk>/qrcode/", views.postazione_qrcode, name="postazione_qrcode"),

    # Interventi
    path("<int:inst_pk>/intervento/nuovo/", views.intervento_create, name="intervento_create"),
    path("intervento/<int:pk>/", views.intervento_detail, name="intervento_detail"),
    path("intervento/<int:pk>/elimina/", views.intervento_delete, name="intervento_delete"),
]
