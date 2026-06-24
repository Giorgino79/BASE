from django.contrib import admin
from .models import Servizio, Contratto, ContrattoFiliale, ContrattoFilialeRiga, ContrattoRiga, ODS, ODSRiga, ConsumoMateriale


@admin.register(Servizio)
class ServizioAdmin(admin.ModelAdmin):
    list_display = ["nome", "tariffa_cartello", "attivo", "richiede_installazione"]
    list_filter = ["attivo", "richiede_installazione"]
    search_fields = ["nome"]


class ContrattoRigaInline(admin.TabularInline):
    model = ContrattoRiga
    extra = 1
    fields = ["servizio", "prezzo"]


class ContrattoFilialeRigaInline(admin.TabularInline):
    model = ContrattoFilialeRiga
    extra = 1
    fields = ["servizio", "prezzo"]


class ContrattoFilialeInline(admin.TabularInline):
    model = ContrattoFiliale
    extra = 0
    fields = ["filiale", "note"]


@admin.register(Contratto)
class ContrattoAdmin(admin.ModelAdmin):
    list_display = ["cliente", "periodicita", "stato", "data_inizio"]
    list_filter = ["stato", "periodicita"]
    search_fields = ["cliente__ragione_sociale", "righe__servizio__nome"]
    inlines = [ContrattoRigaInline, ContrattoFilialeInline]


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
