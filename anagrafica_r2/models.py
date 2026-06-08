from django.db import models
from django.urls import reverse
from core.models_legacy import AllegatiMixin
import re


class Azienda(AllegatiMixin, models.Model):

    TIPO_PAGAMENTO_CHOICES = [
        ('immediato', 'Immediato'),
        ('30_gg',     '30 gg d.f.'),
        ('60_gg',     '60 gg d.f.'),
        ('90_gg',     '90 gg d.f.'),
        ('120_gg',    '120 gg d.f.'),
    ]

    # Sede legale / dati anagrafici
    ragione_sociale   = models.CharField(max_length=200, verbose_name='Ragione Sociale')
    indirizzo         = models.CharField(max_length=200, verbose_name='Indirizzo Sede Legale')
    citta             = models.CharField(max_length=100, verbose_name='Città')
    zona              = models.CharField(max_length=100, verbose_name='Zona')
    cap               = models.CharField(max_length=5,   verbose_name='CAP')
    provincia         = models.CharField(max_length=5,   verbose_name='Provincia', blank=True)

    # Dati fiscali
    partita_iva       = models.CharField(max_length=15, verbose_name='Partita IVA')
    codice_fiscale    = models.CharField(max_length=16, verbose_name='Codice Fiscale', blank=True)
    codice_univoco    = models.CharField(max_length=7,  verbose_name='Codice Univoco SDI', blank=True)
    pec               = models.EmailField(verbose_name='PEC')

    # Referente principale
    referente         = models.CharField(max_length=200, verbose_name='Referente Principale', blank=True)
    telefono          = models.CharField(max_length=20,  verbose_name='Telefono')

    # Email per funzione (specifico per clienti strutturati)
    email_direzione        = models.EmailField(blank=True, verbose_name='Email Direzione',
                                               help_text='Per contratti e comunicazioni direzionali')
    email_amministrazione  = models.EmailField(blank=True, verbose_name='Email Amministrazione',
                                               help_text='Per fatture e pagamenti')
    email_operativo        = models.EmailField(verbose_name='Email Operativo',
                                               help_text='Per pianificazione interventi e rapporti')
    email_operativo_2      = models.EmailField(blank=True, verbose_name='Email Operativo 2',
                                               help_text='Contatto operativo aggiuntivo')

    # Identità commerciale
    marchio           = models.CharField(max_length=200, blank=True, verbose_name='Marchio',
                                         help_text='Nome commerciale / marchio (se diverso dalla ragione sociale)')

    # Dati commerciali
    tipo_pagamento    = models.CharField(max_length=20, choices=TIPO_PAGAMENTO_CHOICES,
                                         default='immediato', verbose_name='Modalità Pagamento')

    # Stato
    installato        = models.BooleanField(default=False, verbose_name='Installazione Completata',
                                             help_text='Tutte le stazioni sono state installate')
    attivo            = models.BooleanField(default=True, verbose_name='Attivo')
    note              = models.TextField(blank=True, verbose_name='Note')

    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clienti'
        ordering = ['ragione_sociale']

    def __str__(self):
        return self.ragione_sociale

    def get_absolute_url(self):
        return reverse('anagrafica:azienda_detail', kwargs={'pk': self.pk})

    @property
    def n_filiali(self):
        return self.filiali.count()

    @property
    def n_filiali_installate(self):
        return self.filiali.filter(installato=True).count()


class Filiale(AllegatiMixin, models.Model):

    TIPO_SEDE_CHOICES = [
        ('punto_vendita', 'Punto Vendita'),
        ('magazzino',     'Magazzino'),
        ('ufficio',       'Ufficio'),
        ('deposito',      'Deposito'),
        ('laboratorio',   'Laboratorio'),
        ('altro',         'Altro'),
    ]

    GIORNO_CHIUSURA_CHOICES = [
        ('',          'Nessun giorno di chiusura'),
        ('lunedi',    'Lunedì'),
        ('martedi',   'Martedì'),
        ('mercoledi', 'Mercoledì'),
        ('giovedi',   'Giovedì'),
        ('venerdi',   'Venerdì'),
        ('sabato',    'Sabato'),
        ('domenica',  'Domenica'),
    ]

    cliente    = models.ForeignKey(Azienda, on_delete=models.CASCADE,
                                    related_name='filiali', verbose_name='Cliente')

    # Identificazione
    nome       = models.CharField(max_length=200, verbose_name='Nome Sede / Punto Vendita')
    tipo_sede  = models.CharField(max_length=20, choices=TIPO_SEDE_CHOICES,
                                   default='punto_vendita', verbose_name='Tipo Sede')

    # Indirizzo sede
    indirizzo  = models.CharField(max_length=200, verbose_name='Indirizzo')
    citta      = models.CharField(max_length=100, verbose_name='Città')
    zona       = models.CharField(max_length=100, verbose_name='Zona')
    cap        = models.CharField(max_length=5,   verbose_name='CAP')
    provincia  = models.CharField(max_length=5,   verbose_name='Provincia', blank=True)

    # Contatti sede
    telefono         = models.CharField(max_length=20, blank=True, verbose_name='Telefono')
    email            = models.EmailField(blank=True, verbose_name='Email')
    referente_nome   = models.CharField(max_length=100, blank=True, verbose_name='Nome Referente')
    referente_tel    = models.CharField(max_length=20,  blank=True, verbose_name='Tel. Referente')
    referente_email  = models.EmailField(blank=True, verbose_name='Email Referente')

    # Logistica servizio
    orario_apertura  = models.CharField(max_length=100, blank=True, verbose_name='Orario Apertura',
                                         help_text='Es: 08:00-20:00 / Lun-Sab')
    giorno_chiusura  = models.CharField(max_length=20, choices=GIORNO_CHIUSURA_CHOICES,
                                         blank=True, default='', verbose_name='Giorno di Chiusura')
    note_accesso     = models.TextField(blank=True, verbose_name='Note Accesso',
                                         help_text='Istruzioni per accedere alla sede (citofono, portone, ecc.)')

    # Stato
    installato  = models.BooleanField(default=False, verbose_name='Installazione Completata')
    attivo      = models.BooleanField(default=True,  verbose_name='Attivo')
    note        = models.TextField(blank=True, verbose_name='Note')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Filiale / Sede'
        verbose_name_plural = 'Filiali / Sedi'
        ordering = ['cliente__ragione_sociale', 'nome']

    def __str__(self):
        return f'{self.cliente.ragione_sociale} — {self.nome}'

    def get_absolute_url(self):
        return reverse('anagrafica:filiale_detail', kwargs={'pk': self.pk})

    def get_indirizzo_completo(self):
        parts = [self.indirizzo, f'{self.cap} {self.citta}'.strip()]
        return ', '.join(p for p in parts if p.strip())


class Privato(AllegatiMixin, models.Model):

    nome             = models.CharField(max_length=100, verbose_name='Nome')
    cognome          = models.CharField(max_length=100, verbose_name='Cognome')
    telefono         = models.CharField(max_length=20, verbose_name='Telefono')
    indirizzo        = models.CharField(max_length=200, verbose_name='Indirizzo (via)')
    citta            = models.CharField(max_length=100, verbose_name='Città')
    zona             = models.CharField(max_length=100, verbose_name='Zona')

    codice_fiscale   = models.CharField(max_length=16, blank=True, verbose_name='Codice Fiscale')
    email            = models.EmailField(blank=True, verbose_name='Email')
    cap              = models.CharField(max_length=5, blank=True, verbose_name='CAP')
    provincia        = models.CharField(max_length=5, blank=True, verbose_name='Provincia')

    attivo           = models.BooleanField(default=True, verbose_name='Attivo')
    note             = models.TextField(blank=True, verbose_name='Note')

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente Privato'
        verbose_name_plural = 'Clienti Privati'
        ordering = ['cognome', 'nome']

    def __str__(self):
        return f'{self.cognome} {self.nome}'

    def get_absolute_url(self):
        return reverse('anagrafica:privato_detail', kwargs={'pk': self.pk})

    @property
    def nome_completo(self):
        return f'{self.cognome} {self.nome}'

    def get_indirizzo_completo(self):
        return f'{self.indirizzo}, {self.citta}'


class Fornitore(AllegatiMixin, models.Model):

    CATEGORIA_CHOICES = [
        ('materie_prime', 'Materie Prime'),
        ('semilavorati',  'Semilavorati'),
        ('servizi',       'Servizi'),
        ('consulenza',    'Consulenza'),
        ('software',      'Software/IT'),
        ('trasporti',     'Trasporti e Logistica'),
        ('altri',         'Altri'),
    ]

    TIPO_PAGAMENTO_CHOICES = [
        ('bonifico_30',  'Bonifico 30 gg'),
        ('bonifico_60',  'Bonifico 60 gg'),
        ('bonifico_90',  'Bonifico 90 gg'),
        ('bonifico_120', 'Bonifico 120 gg'),
        ('rid_30',       'RID 30 gg'),
        ('rid_60',       'RID 60 gg'),
        ('riba_30',      'RIBA 30 gg'),
        ('riba_60',      'RIBA 60 gg'),
        ('contrassegno', 'Contrassegno'),
        ('anticipo',     'Anticipo 100%'),
        ('fine_mese',    'Fine Mese'),
        ('immediato',    'Pagamento Immediato'),
    ]

    PRIORITA_CHOICES = [
        ('critica', 'Critica (Urgente)'),
        ('alta',    'Alta (Prioritaria)'),
        ('media',   'Media (Normale)'),
        ('bassa',   'Bassa (Differibile)'),
    ]

    ragione_sociale     = models.CharField(max_length=200, verbose_name='Ragione Sociale')
    indirizzo           = models.CharField(max_length=200, blank=True, verbose_name='Indirizzo')
    citta               = models.CharField(max_length=100, blank=True, verbose_name='Città')
    cap                 = models.CharField(max_length=5,   blank=True, verbose_name='CAP')
    provincia           = models.CharField(max_length=5,   blank=True, verbose_name='Provincia')
    regione             = models.CharField(max_length=100, blank=True, verbose_name='Regione')
    telefono            = models.CharField(max_length=20,  verbose_name='Telefono')
    email               = models.EmailField(verbose_name='Email')

    partita_iva         = models.CharField(max_length=15, verbose_name='Partita IVA')
    codice_fiscale      = models.CharField(max_length=16, blank=True, verbose_name='Codice Fiscale')
    pec                 = models.EmailField(blank=True, verbose_name='PEC')
    codice_destinatario = models.CharField(max_length=7, blank=True, verbose_name='Codice SDI')
    iban                = models.CharField(max_length=34, blank=True, verbose_name='IBAN')

    categoria           = models.CharField(max_length=20, choices=CATEGORIA_CHOICES,
                                           default='altri', verbose_name='Categoria')
    tipo_pagamento      = models.CharField(max_length=20, choices=TIPO_PAGAMENTO_CHOICES,
                                           default='bonifico_30', verbose_name='Tipo Pagamento')
    priorita_pagamento  = models.CharField(max_length=10, choices=PRIORITA_CHOICES,
                                           default='media', verbose_name='Priorità Pagamento')

    referente_nome      = models.CharField(max_length=100, blank=True, verbose_name='Nome Referente')
    referente_telefono  = models.CharField(max_length=20,  blank=True, verbose_name='Tel. Referente')
    referente_email     = models.EmailField(blank=True, verbose_name='Email Referente')

    attivo      = models.BooleanField(default=True, verbose_name='Attivo')
    note        = models.TextField(blank=True, verbose_name='Note')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fornitore'
        verbose_name_plural = 'Fornitori'
        ordering = ['ragione_sociale']

    def __str__(self):
        return self.ragione_sociale

    def get_absolute_url(self):
        return reverse('anagrafica:fornitore_detail', kwargs={'pk': self.pk})

    def get_indirizzo_completo(self):
        parts = [self.indirizzo, f'{self.cap} {self.citta}'.strip()]
        return ', '.join(p for p in parts if p.strip()) or '—'

    def has_referente(self):
        return bool(self.referente_nome or self.referente_telefono or self.referente_email)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.iban:
            iban = self.iban.replace(' ', '').upper()
            if not iban.startswith('IT') or len(iban) != 27:
                raise ValidationError({'iban': 'IBAN non valido (formato: IT + 25 caratteri)'})
