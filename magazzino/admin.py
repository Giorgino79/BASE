from django.contrib import admin
from .models import Categoria, Prodotto, Ricezione, RigaRicezione


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "attiva"]
    list_filter = ["attiva"]


class RigaRicezioneInline(admin.TabularInline):
    model = RigaRicezione
    extra = 1


@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    list_display = ["nome_prodotto", "categoria", "unita_misura", "is_biocida", "attivo"]
    list_filter = ["categoria", "attivo", "is_biocida", "unita_misura"]
    search_fields = ["nome_prodotto", "codice_interno", "codice_fornitore"]


@admin.register(Ricezione)
class RicezioneAdmin(admin.ModelAdmin):
    list_display = ["__str__", "fornitore", "data_ricezione", "ordine"]
    list_filter = ["data_ricezione"]
    search_fields = ["numero_ddt", "fornitore__ragione_sociale"]
    inlines = [RigaRicezioneInline]
