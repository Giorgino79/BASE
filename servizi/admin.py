from django.contrib import admin
from .models import Servizio, Contratto, ContrattoFiliale, ODS, ODSRiga, ConsumoMateriale


@admin.register(Servizio)
class ServizioAdmin(admin.ModelAdmin):
    list_display = ["nome", "tariffa_cartello", "attivo"]
    list_filter = ["attivo"]
    search_fields = ["nome"]


class ContrattoFilialeInline(admin.TabularInline):
    model = ContrattoFiliale
    extra = 0
    fields = ["filiale", "prezzo_override", "note"]


@admin.register(Contratto)
class ContrattoAdmin(admin.ModelAdmin):
    list_display = ["cliente", "servizio", "prezzo_default", "periodicita", "stato", "data_inizio"]
    list_filter = ["stato", "periodicita"]
    search_fields = ["cliente__ragione_sociale", "servizio__nome"]
    inlines = [ContrattoFilialeInline]


class ODSRigaInline(admin.TabularInline):
    model = ODSRiga
    extra = 0
    fields = ["ordine", "servizio", "prezzo", "contratto_filiale", "note"]


@admin.register(ODS)
class ODSAdmin(admin.ModelAdmin):
    list_display = ["numero", "cliente_display", "data_servizio", "stato", "tecnico"]
    list_filter = ["stato"]
    search_fields = ["numero", "filiale__cliente__ragione_sociale", "privato__cognome"]
    readonly_fields = ["numero"]
    inlines = [ODSRigaInline]
