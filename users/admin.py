"""
Admin configuration per l'app users.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Timbratura,
    GiornataLavorativa,
    RichiestaFerie,
    RichiestaPermesso,
    LetteraRichiamo,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "codice_dipendente",
        "get_full_name",
        "email",
        "qualifica",
        "stato",
        "is_staff",
    ]
    list_filter = ["stato", "is_staff", "is_superuser", "qualifica", "reparto"]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "codice_dipendente",
        "codice_fiscale",
    ]
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Dati Dipendente",
            {
                "fields": (
                    "codice_dipendente",
                    "stato",
                    "qualifica",
                    "reparto",
                    "foto_profilo",
                )
            },
        ),
        (
            "Dati Anagrafici",
            {"fields": ("data_nascita", "luogo_nascita", "codice_fiscale")},
        ),
        (
            "Contatti",
            {
                "fields": (
                    "telefono",
                    "telefono_emergenza",
                    "indirizzo",
                    "citta",
                    "cap",
                    "provincia",
                )
            },
        ),
        ("Dati Lavorativi", {"fields": ("data_assunzione", "data_cessazione")}),
        (
            "Ferie e Permessi",
            {
                "fields": (
                    "giorni_ferie_anno",
                    "giorni_ferie_residui",
                    "ore_permesso_residue",
                )
            },
        ),
        ("Note", {"fields": ("note_interne",)}),
    )


@admin.register(Timbratura)
class TimbraturaAdmin(admin.ModelAdmin):
    list_display = ["user", "data", "ora", "tipo", "turno"]
    list_filter = ["tipo", "turno", "data"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    date_hierarchy = "data"


@admin.register(GiornataLavorativa)
class GiornataLavorativaAdmin(admin.ModelAdmin):
    list_display = ["user", "data", "ore_totali", "ore_straordinarie", "conclusa"]
    list_filter = ["conclusa", "data"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    date_hierarchy = "data"


@admin.register(RichiestaFerie)
class RichiestaFerieAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "data_inizio",
        "data_fine",
        "giorni_richiesti",
        "stato",
        "gestita_da",
    ]
    list_filter = ["stato", "data_inizio"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    date_hierarchy = "data_inizio"


@admin.register(RichiestaPermesso)
class RichiestaPermessoAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "data",
        "ora_inizio",
        "ora_fine",
        "ore_richieste",
        "stato",
        "gestita_da",
    ]
    list_filter = ["stato", "data"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    date_hierarchy = "data"


@admin.register(LetteraRichiamo)
class LetteraRichiamoAdmin(admin.ModelAdmin):
    list_display = ["user", "tipo", "data_emissione", "emessa_da", "user_ha_letto"]
    list_filter = ["tipo", "user_ha_letto", "data_emissione"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "motivo"]
    date_hierarchy = "data_emissione"
