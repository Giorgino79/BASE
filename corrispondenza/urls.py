from django.urls import path
from . import views

app_name = 'corrispondenza'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nuova/', views.crea, name='crea'),
    path('<int:pk>/', views.dettaglio, name='dettaglio'),
    path('<int:pk>/modifica/', views.modifica, name='modifica'),
    path('<int:pk>/elimina/', views.elimina, name='elimina'),
    path('<int:pk>/invia/', views.invia, name='invia'),
    path('<int:pk>/archivia/', views.archivia, name='archivia'),
    path('<int:pk>/duplica/', views.duplica, name='duplica'),
    path('<int:pk>/pdf/', views.pdf, name='pdf'),
    path('tipi/', views.tipi_lista, name='tipi_lista'),
    path('tipi/<int:pk>/modifica/', views.tipo_modifica, name='tipo_modifica'),
    path('tipi/<int:pk>/elimina/', views.tipo_elimina, name='tipo_elimina'),
]
