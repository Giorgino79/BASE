from django.contrib import admin
from .models import Corrispondenza, TipoCorrispondenza

@admin.register(TipoCorrispondenza)
class TipoCorrispondenzaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'attivo']
    list_filter = ['attivo']

@admin.register(Corrispondenza)
class CorrispondenzaAdmin(admin.ModelAdmin):
    list_display = ['numero_protocollo', 'oggetto', 'stato', 'priorita', 'creato_da', 'created_at']
    list_filter = ['stato', 'priorita', 'tipo_destinatario']
    search_fields = ['oggetto', 'numero_protocollo', 'destinatario_nome']
    readonly_fields = ['numero_protocollo', 'created_at', 'updated_at']
