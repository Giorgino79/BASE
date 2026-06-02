from django.contrib import admin
from .models import OrdineAcquisto, RigaOrdine, FatturaPassiva


class RigaOrdineInline(admin.TabularInline):
    model = RigaOrdine
    extra = 1


@admin.register(OrdineAcquisto)
class OrdineAcquistoAdmin(admin.ModelAdmin):
    list_display = ["numero_ordine", "fornitore", "data_ordine", "stato"]
    list_filter = ["stato"]
    search_fields = ["numero_ordine", "fornitore__ragione_sociale"]
    inlines = [RigaOrdineInline]


@admin.register(FatturaPassiva)
class FatturaPassivaAdmin(admin.ModelAdmin):
    list_display = ["numero_fattura", "fornitore", "data_fattura", "totale", "stato_pagamento"]
    list_filter = ["stato_pagamento"]
    search_fields = ["numero_fattura", "fornitore__ragione_sociale"]
