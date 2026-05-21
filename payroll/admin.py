from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CCNL,
    LivelloInquadramento,
    ElementoRetributivo,
    DatiContrattualiPayroll,
    BustaPaga,
    VoceBustaPaga,
    FeriePermessiPayroll,
    ManualePayroll,
)


class LivelloInquadramentoInline(admin.TabularInline):
    model = LivelloInquadramento
    extra = 1
    fields = ("codice", "descrizione", "paga_base_mensile", "ore_settimanali_standard")


class ElementoRetributivoInline(admin.TabularInline):
    model = ElementoRetributivo
    extra = 1
    fields = ("codice", "nome", "tipo_calcolo", "valore", "natura", "incluso_tfr", "incluso_tredicesima", "attivo")


@admin.register(CCNL)
class CCNLAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "data_inizio_validita", "giorni_ferie_annui", "ore_rol_annue", "ha_tredicesima", "ha_quattordicesima"]
    list_filter = ["tipo", "ha_tredicesima", "ha_quattordicesima"]
    search_fields = ["nome"]
    date_hierarchy = "data_inizio_validita"
    inlines = [LivelloInquadramentoInline, ElementoRetributivoInline]

    fieldsets = (
        ("Informazioni Generali", {"fields": ("nome", "tipo", "data_inizio_validita", "data_fine_validita")}),
        ("Ferie e Permessi", {"fields": ("giorni_ferie_annui", "ore_rol_annue", "ore_permessi_retribuiti_annui")}),
        ("Straordinari", {"fields": ("percentuale_straordinario_feriale", "percentuale_straordinario_festivo", "percentuale_straordinario_notturno")}),
        ("Mensilità Aggiuntive", {"fields": ("ha_tredicesima", "ha_quattordicesima", "maturazione_quattordicesima")}),
        ("Scatti di Anzianità", {"fields": ("ha_scatti_anzianita", "anni_per_scatto", "importo_scatto", "numero_massimo_scatti")}),
        ("Note", {"fields": ("note",)}),
    )


@admin.register(LivelloInquadramento)
class LivelloInquadramentoAdmin(admin.ModelAdmin):
    list_display = ["ccnl", "codice", "descrizione", "paga_base_mensile_formatted", "ore_settimanali_standard"]
    list_filter = ["ccnl"]
    search_fields = ["codice", "descrizione", "ccnl__nome"]

    def paga_base_mensile_formatted(self, obj):
        return f"€ {obj.paga_base_mensile:,.2f}"
    paga_base_mensile_formatted.short_description = "Paga Base Mensile"


@admin.register(ElementoRetributivo)
class ElementoRetributivoAdmin(admin.ModelAdmin):
    list_display = ["ccnl", "codice", "nome", "tipo_calcolo", "valore_formatted", "natura", "attivo"]
    list_filter = ["ccnl", "tipo_calcolo", "natura", "attivo"]
    search_fields = ["codice", "nome", "ccnl__nome"]

    def valore_formatted(self, obj):
        if obj.tipo_calcolo in ["PERCENTUALE_PAGA_BASE", "PERCENTUALE_RETRIBUZIONE"]:
            return f"{obj.valore}%"
        return f"€ {obj.valore:,.2f}"
    valore_formatted.short_description = "Valore"


@admin.register(DatiContrattualiPayroll)
class DatiContrattualiPayrollAdmin(admin.ModelAdmin):
    list_display = ["user", "ccnl", "livello", "tipo_contratto", "ore_settimanali", "superminimo_formatted"]
    list_filter = ["ccnl", "tipo_contratto"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "user__codice_fiscale"]

    fieldsets = (
        ("Dipendente", {"fields": ("user",)}),
        ("Dati Contrattuali", {"fields": ("ccnl", "livello", "tipo_contratto", "data_fine_contratto", "data_cessazione")}),
        ("Orario e Retribuzione", {"fields": ("ore_settimanali", "percentuale_part_time", "superminimo")}),
        ("Dati Fiscali", {"fields": ("aliquota_addizionale_regionale", "aliquota_addizionale_comunale")}),
        ("Detrazioni", {"fields": ("detrazione_lavoro_dipendente", "coniuge_a_carico", "numero_figli_a_carico", "altri_familiari_a_carico")}),
        ("Bonifico", {"fields": ("iban",)}),
    )

    def superminimo_formatted(self, obj):
        return f"€ {obj.superminimo:,.2f}" if obj.superminimo > 0 else "-"
    superminimo_formatted.short_description = "Superminimo"


class VoceBustaPagaInline(admin.TabularInline):
    model = VoceBustaPaga
    extra = 0
    can_delete = False
    readonly_fields = ["tipo", "descrizione", "quantita", "importo_unitario", "importo_totale"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BustaPaga)
class BustaPagaAdmin(admin.ModelAdmin):
    list_display = ["user", "periodo", "ore_totali", "imponibile_formatted", "netto_formatted", "status_badge"]
    list_filter = ["anno", "mese", "confermata"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    date_hierarchy = "data_elaborazione"
    readonly_fields = ["data_elaborazione", "imponibile_fiscale", "imponibile_contributivo", "ritenute_previdenziali", "ritenute_irpef", "addizionale_regionale", "addizionale_comunale", "detrazioni_fiscali", "netto_busta", "tfr_maturato"]
    inlines = [VoceBustaPagaInline]
    actions = ["conferma_buste", "annulla_conferma_buste"]

    fieldsets = (
        ("Informazioni Generali", {"fields": ("user", "mese", "anno", "data_elaborazione", "confermata")}),
        ("Ore Lavorate", {"fields": ("ore_ordinarie", "ore_straordinario_feriale", "ore_straordinario_festivo", "ore_straordinario_notturno")}),
        ("Assenze", {"fields": ("ore_ferie", "ore_rol", "ore_permessi", "ore_malattia")}),
        ("Retribuzione Lorda", {"fields": ("imponibile_fiscale", "imponibile_contributivo")}),
        ("Trattenute", {"fields": ("ritenute_previdenziali", "ritenute_irpef", "addizionale_regionale", "addizionale_comunale", "altre_trattenute")}),
        ("Detrazioni e Netto", {"fields": ("detrazioni_fiscali", "netto_busta", "tfr_maturato")}),
    )

    def periodo(self, obj):
        return f"{obj.mese:02d}/{obj.anno}"
    periodo.short_description = "Periodo"

    def ore_totali(self, obj):
        tot = obj.ore_ordinarie + obj.ore_straordinario_feriale + obj.ore_straordinario_festivo + obj.ore_straordinario_notturno
        return f"{tot:.2f}h"
    ore_totali.short_description = "Ore Totali"

    def imponibile_formatted(self, obj):
        return f"€ {obj.imponibile_fiscale:,.2f}"
    imponibile_formatted.short_description = "Imponibile"
    imponibile_formatted.admin_order_field = "imponibile_fiscale"

    def netto_formatted(self, obj):
        return format_html('<strong style="color:#198754;">€ {:,.2f}</strong>', obj.netto_busta)
    netto_formatted.short_description = "Netto"
    netto_formatted.admin_order_field = "netto_busta"

    def status_badge(self, obj):
        if obj.confermata:
            return format_html('<span style="background:#198754;color:white;padding:3px 10px;border-radius:3px;">Confermata</span>')
        return format_html('<span style="background:#ffc107;color:black;padding:3px 10px;border-radius:3px;">Bozza</span>')
    status_badge.short_description = "Stato"

    def conferma_buste(self, request, queryset):
        count = queryset.update(confermata=True)
        self.message_user(request, f"{count} buste paga confermate.")
    conferma_buste.short_description = "Conferma buste paga selezionate"

    def annulla_conferma_buste(self, request, queryset):
        count = queryset.update(confermata=False)
        self.message_user(request, f"{count} buste paga riportate in bozza.")
    annulla_conferma_buste.short_description = "Riporta in bozza buste selezionate"


@admin.register(FeriePermessiPayroll)
class FeriePermessiPayrollAdmin(admin.ModelAdmin):
    list_display = ["user", "anno", "tipo", "ore_maturate", "ore_godute", "ore_residue_display"]
    list_filter = ["anno", "tipo"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    fields = ("user", "anno", "tipo", "ore_maturate", "ore_residuo_anno_precedente", "ore_godute")

    def ore_residue_display(self, obj):
        color = "#198754" if obj.ore_residue > 0 else "#dc3545"
        return format_html('<strong style="color:{};">{:.2f}h</strong>', color, obj.ore_residue)
    ore_residue_display.short_description = "Ore Residue"


@admin.register(ManualePayroll)
class ManualePayrollAdmin(admin.ModelAdmin):
    list_display = ["titolo", "versione", "data_ultima_modifica", "modificato_da", "preview_contenuto"]
    search_fields = ["titolo", "contenuto"]
    readonly_fields = ["data_ultima_modifica", "modificato_da"]
    fields = ("titolo", "versione", "contenuto", "data_ultima_modifica", "modificato_da")

    def preview_contenuto(self, obj):
        return obj.contenuto[:100] + "..." if len(obj.contenuto) > 100 else obj.contenuto
    preview_contenuto.short_description = "Anteprima"

    def save_model(self, request, obj, form, change):
        obj.modificato_da = request.user
        super().save_model(request, obj, form, change)
