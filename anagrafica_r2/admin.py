from django.contrib import admin
from .models import Azienda, Filiale


class FilialeInline(admin.TabularInline):
    model = Filiale
    extra = 0
    fields = ['nome', 'tipo_sede', 'citta', 'telefono', 'installato', 'attivo']
    show_change_link = True


@admin.register(Azienda)
class AziendaAdmin(admin.ModelAdmin):
    list_display  = ['ragione_sociale', 'citta', 'telefono', 'tipo_pagamento',
                     'n_filiali', 'installato', 'attivo', 'created_at']
    list_filter   = ['attivo', 'installato', 'tipo_pagamento']
    search_fields = ['ragione_sociale', 'partita_iva', 'codice_fiscale', 'citta']
    list_per_page = 25
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FilialeInline]

    fieldsets = (
        ('Sede Legale', {
            'fields': ('ragione_sociale', 'indirizzo', 'citta', 'cap', 'provincia')
        }),
        ('Dati Fiscali', {
            'fields': ('partita_iva', 'codice_fiscale', 'codice_univoco', 'pec')
        }),
        ('Referente e Telefono', {
            'fields': ('referente', 'telefono')
        }),
        ('Email per Funzione', {
            'fields': ('email_direzione', 'email_amministrazione',
                       'email_operativo', 'email_operativo_2')
        }),
        ('Dati Commerciali', {
            'fields': ('tipo_pagamento',)
        }),
        ('Stato', {
            'fields': ('installato', 'attivo', 'note')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Sedi')
    def n_filiali(self, obj):
        return obj.filiali.count()


@admin.register(Filiale)
class FilialeAdmin(admin.ModelAdmin):
    list_display  = ['nome', 'cliente', 'tipo_sede', 'citta', 'installato', 'attivo']
    list_filter   = ['attivo', 'installato', 'tipo_sede']
    search_fields = ['nome', 'cliente__ragione_sociale', 'citta']
    raw_id_fields = ['cliente']
    list_per_page = 25
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Cliente', {
            'fields': ('cliente',)
        }),
        ('Identificazione', {
            'fields': ('nome', 'tipo_sede')
        }),
        ('Indirizzo Sede', {
            'fields': ('indirizzo', 'citta', 'cap', 'provincia', 'regione')
        }),
        ('Contatti Sede', {
            'fields': ('telefono', 'email',
                       'referente_nome', 'referente_tel', 'referente_email')
        }),
        ('Logistica Servizio', {
            'fields': ('orario_apertura', 'giorno_chiusura', 'note_accesso')
        }),
        ('Stato', {
            'fields': ('installato', 'attivo', 'note')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
