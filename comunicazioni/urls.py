from django.urls import path
from . import views

app_name = 'comunicazioni'

urlpatterns = [
    # Promemoria
    path('promemoria/', views.promemoria_list, name='promemoria_list'),
    path('promemoria/nuovo/', views.promemoria_create, name='promemoria_create'),
    path('promemoria/<int:pk>/modifica/', views.promemoria_update, name='promemoria_update'),
    path('promemoria/<int:pk>/elimina/', views.promemoria_delete, name='promemoria_delete'),
    path('promemoria/<int:pk>/toggle/', views.promemoria_toggle, name='promemoria_toggle'),
    # Chat
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/nuova/', views.chat_nuova, name='chat_nuova'),
    path('chat/<int:pk>/', views.chat_detail, name='chat_detail'),
    path('chat/<int:pk>/api/', views.chat_messages_api, name='chat_messages_api'),
]
