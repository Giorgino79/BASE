from django.contrib import admin
from .models import WAConfig, WAMessaggio, WABroadcast, WABroadcastDestinatario


@admin.register(WAConfig)
class WAConfigAdmin(admin.ModelAdmin):
    list_display = ["numero_mittente", "attivo", "delay_min", "delay_max"]


@admin.register(WAMessaggio)
class WAMessaggioAdmin(admin.ModelAdmin):
    list_display = ["destinatario_nome", "destinatario_numero", "stato", "tipo", "inviato_at", "created_at"]
    list_filter = ["stato", "tipo"]
    search_fields = ["destinatario_nome", "destinatario_numero", "testo"]


class WABroadcastDestinatarioInline(admin.TabularInline):
    model = WABroadcastDestinatario
    extra = 0
    readonly_fields = ["stato", "inviato_at", "errore"]


@admin.register(WABroadcast)
class WABroadcastAdmin(admin.ModelAdmin):
    list_display = ["titolo", "stato", "avviato_at", "completato_at"]
    list_filter = ["stato"]
    inlines = [WABroadcastDestinatarioInline]
