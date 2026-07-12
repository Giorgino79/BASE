from django.contrib import admin
from .models import Installazione, Postazione, InterventoInstallazione, RiscontroPostazione


class PostazioneInline(admin.TabularInline):
    model = Postazione
    extra = 0
    fields = ["numero", "descrizione_luogo", "ha_cartello", "numero_cartello"]
    readonly_fields = ["numero"]


class InterventoInline(admin.TabularInline):
    model = InterventoInstallazione
    extra = 0
    fields = ["data_intervento", "tecnico", "prodotto", "quantita_prodotto"]
    readonly_fields = []


@admin.register(Installazione)
class InstallazioneAdmin(admin.ModelAdmin):
    list_display = ["numero", "cliente_display", "servizio", "data_installazione", "stato", "attiva", "n_postazioni"]
    list_filter = ["stato", "attiva", "servizio"]
    search_fields = ["numero"]
    inlines = [PostazioneInline, InterventoInline]
    readonly_fields = ["numero"]


@admin.register(Postazione)
class PostazioneAdmin(admin.ModelAdmin):
    list_display = ["__str__", "installazione", "numero", "ha_cartello", "numero_cartello"]
    list_filter = ["ha_cartello", "installazione__servizio"]
    search_fields = ["installazione__numero", "descrizione_luogo"]


class RiscontroInline(admin.TabularInline):
    model = RiscontroPostazione
    extra = 0
    fields = ["postazione", "esito", "note"]


@admin.register(InterventoInstallazione)
class InterventoInstallazioneAdmin(admin.ModelAdmin):
    list_display = ["__str__", "installazione", "data_intervento", "tecnico"]
    list_filter = ["data_intervento", "tecnico"]
    inlines = [RiscontroInline]
