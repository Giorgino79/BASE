from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.mixins import AllegatiMixin


class ContoContabile(models.Model):
    """
    Conto del libro mastro semplificato.
    Ogni cliente, fornitore, cassa e banca ha il proprio conto.
    """

    class Tipo(models.TextChoices):
        CLIENTE      = 'cliente',      'Cliente'
        FORNITORE    = 'fornitore',    'Fornitore'
        CASSA        = 'cassa',        'Cassa'
        BANCA        = 'banca',        'Banca'
        CUSTODIA     = 'custodia',     'Custodia (persona)'
        IVA_CREDITO  = 'iva_credito',  'IVA a credito'
        IVA_DEBITO   = 'iva_debito',   'IVA a debito'
        GENERICO     = 'generico',     'Generico'

    nome        = models.CharField(max_length=200, verbose_name='Nome conto')
    tipo        = models.CharField(max_length=20, choices=Tipo.choices, verbose_name='Tipo')
    iban        = models.CharField(
        max_length=34, blank=True, verbose_name='IBAN',
        help_text='Solo per conti di tipo Banca',
    )
    descrizione = models.TextField(blank=True, verbose_name='Descrizione / note')
    attivo      = models.BooleanField(default=True, verbose_name='Attivo')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Conto Contabile'
        verbose_name_plural = 'Conti Contabili'
        ordering            = ['tipo', 'nome']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.nome}'

    def get_absolute_url(self):
        return reverse('contabilita:mastrino', kwargs={'pk': self.pk})

    @property
    def saldo(self):
        from django.db.models import Sum
        d = self.movimenti_dare.aggregate(tot=Sum('importo'))['tot'] or Decimal('0.00')
        a = self.movimenti_avere.aggregate(tot=Sum('importo'))['tot'] or Decimal('0.00')
        return d - a


class ImpostazioniContabilita(models.Model):
    """
    Impostazioni di riga singola (pk=1). Per ora ne contiene una sola: fino a
    quando la contabilità è chiusa.

    Chiudere un periodo è l'unico modo per impedire che qualcuno infili un
    movimento in un trimestre già liquidato. Non è un vincolo sull'ordine di
    inserimento — quello lo dà `created_at`, che cresce da solo — ma una
    barriera sulla data dell'operazione.
    """

    chiusa_fino_al = models.DateField(
        null=True, blank=True,
        verbose_name='Contabilità chiusa fino al',
        help_text='Nessun movimento potrà avere una data pari o precedente a questa. '
                  'Lascia vuoto per non chiudere niente.',
    )
    aggiornata_da  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='Aggiornata da',
    )
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Impostazioni Contabilità'
        verbose_name_plural = 'Impostazioni Contabilità'

    def __str__(self):
        if self.chiusa_fino_al:
            return f'Contabilità chiusa fino al {self.chiusa_fino_al:%d/%m/%Y}'
        return 'Nessun periodo chiuso'

    def save(self, *args, **kwargs):
        self.pk = 1          # riga unica: non se ne creano altre
        super().save(*args, **kwargs)

    @classmethod
    def carica(cls):
        """L'istanza salvata, o una vuota non persistita se non esiste ancora."""
        return cls.objects.filter(pk=1).first() or cls(pk=1)

    @classmethod
    def chiusura(cls):
        """
        Solo la data di chiusura, con una query leggera: la si interroga a ogni
        salvataggio di movimento, quindi non conviene materializzare la riga.
        """
        return cls.objects.filter(pk=1).values_list('chiusa_fino_al', flat=True).first()


class RegimeIva(models.Model):
    """
    Regime di liquidazione IVA dell'azienda, storicizzato: non "qual è il
    regime oggi" ma "quale regime era vigente in una data data". Un cambio di
    regime non deve mai riscrivere la lettura delle liquidazioni passate —
    per questo non è un campo su un'impostazione singola, ma uno storico con
    validità temporale.
    """

    class Tipo(models.TextChoices):
        MENSILE              = 'mensile',              'Mensile'
        TRIMESTRALE_OPZIONE  = 'trimestrale_opzione',   'Trimestrale per opzione (+1% interessi)'
        TRIMESTRALE_NATURALE = 'trimestrale_naturale',  'Trimestrale naturale (senza interessi)'

    tipo       = models.CharField(max_length=25, choices=Tipo.choices, verbose_name='Regime IVA')
    valido_dal = models.DateField(verbose_name='Valido dal')
    valido_al  = models.DateField(
        null=True, blank=True, verbose_name='Valido fino al',
        help_text='Lascia vuoto se è il regime tuttora in vigore.',
    )
    note       = models.TextField(blank=True, verbose_name='Note')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Regime IVA'
        verbose_name_plural = 'Storico regimi IVA'
        ordering            = ['-valido_dal']

    def __str__(self):
        fino = f' al {self.valido_al:%d/%m/%Y}' if self.valido_al else ' (in corso)'
        return f'{self.get_tipo_display()} dal {self.valido_dal:%d/%m/%Y}{fino}'

    @property
    def ha_interessi(self):
        """Il trimestrale per opzione paga l'1% di interesse, quello naturale no."""
        return self.tipo == self.Tipo.TRIMESTRALE_OPZIONE

    @property
    def periodicita_mesi(self):
        """1 per il mensile, 3 per entrambi i trimestrali."""
        return 1 if self.tipo == self.Tipo.MENSILE else 3

    def save(self, *args, **kwargs):
        # Un solo regime "aperto" alla volta: inserendone uno nuovo senza
        # valido_al, quello precedentemente aperto si chiude da solo il
        # giorno prima. Supporta solo l'aggiunta in coda alla storia, non la
        # correzione di un periodo passato.
        if self.valido_al is None:
            (RegimeIva.objects
             .filter(valido_al__isnull=True)
             .exclude(pk=self.pk)
             .update(valido_al=self.valido_dal - timedelta(days=1)))
        super().save(*args, **kwargs)

    @classmethod
    def vigente_al(cls, data):
        """Il regime in vigore a una certa data, o None se non ancora impostato."""
        return (cls.objects
                .filter(valido_dal__lte=data)
                .filter(models.Q(valido_al__isnull=True) | models.Q(valido_al__gte=data))
                .order_by('-valido_dal')
                .first())


class LiquidazioneIva(models.Model):
    """
    Il versamento IVA di un periodo: quanto è dovuto (o quanto resta a
    credito) e se è già stato versato.

    Le fatture incluse non sono un elenco scelto a mano né una tabella ponte:
    sono quelle i cui movimenti IVA (vedi `MovimentoPrimaNota.liquidazione_iva`)
    vengono agganciati a questa liquidazione. Il dettaglio fattura risale a
    questo oggetto passando dal proprio movimento, non il contrario.
    """

    class Periodicita(models.TextChoices):
        MESE      = 'mese',      'Mensile'
        TRIMESTRE = 'trimestre', 'Trimestrale'

    class Stato(models.TextChoices):
        DA_VERSARE = 'da_versare', 'Da versare'
        VERSATA    = 'versata',    'Versata'

    periodicita = models.CharField(
        max_length=10, choices=Periodicita.choices, verbose_name='Periodicità')
    anno        = models.PositiveSmallIntegerField(verbose_name='Anno')
    periodo     = models.PositiveSmallIntegerField(
        verbose_name='Periodo',
        help_text='Mese (1-12) se mensile, trimestre (1-4) se trimestrale.',
    )

    iva_a_debito       = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='IVA a debito del periodo')
    iva_a_credito       = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='IVA a credito del periodo')
    credito_precedente = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Credito riportato dal periodo precedente',
    )
    interessi          = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Interessi (1% trimestrale per opzione)',
    )

    stato                 = models.CharField(
        max_length=15, choices=Stato.choices, default=Stato.DA_VERSARE, verbose_name='Stato')
    data_versamento       = models.DateField(null=True, blank=True, verbose_name='Data versamento')
    riferimento_pagamento = models.CharField(
        max_length=100, blank=True, verbose_name='Riferimento pagamento',
        help_text='Es. quietanza F24, CRO del bonifico.',
    )

    creato_da  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='+',
        verbose_name='Creata da',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Liquidazione IVA'
        verbose_name_plural = 'Liquidazioni IVA'
        ordering            = ['-anno', '-periodo']
        constraints = [
            models.UniqueConstraint(
                fields=['periodicita', 'anno', 'periodo'],
                name='contabilita_liquidazione_iva_unica_per_periodo',
            ),
        ]

    def __str__(self):
        if self.periodicita == self.Periodicita.TRIMESTRE:
            return f'Liquidazione IVA {self.periodo}° trim. {self.anno}'
        return f'Liquidazione IVA {self.periodo:02d}/{self.anno}'

    def get_absolute_url(self):
        return reverse('contabilita:liquidazione_iva_detail', kwargs={'pk': self.pk})

    @property
    def saldo(self):
        """Positivo: da versare. Negativo: credito da riportare al periodo dopo."""
        return (self.iva_a_debito - self.iva_a_credito
                - self.credito_precedente + self.interessi)

    @property
    def importo_dovuto(self):
        return self.saldo if self.saldo > 0 else Decimal('0.00')

    @property
    def credito_riportato(self):
        return -self.saldo if self.saldo < 0 else Decimal('0.00')


class MovimentoPrimaNota(AllegatiMixin, models.Model):
    """
    Singola riga della prima nota: un dare, un avere, un importo.
    """

    class Tipo(models.TextChoices):
        FATTURA_CLIENTE      = 'fattura_cliente',      'Fattura cliente'
        NOTA_CREDITO_CLIENTE = 'nota_credito_cliente', 'Nota di credito a cliente'
        FATTURA_FORNITORE    = 'fattura_fornitore',    'Fattura fornitore'
        INCASSO              = 'incasso',              'Incasso da cliente'
        PAGAMENTO            = 'pagamento',            'Pagamento a fornitore'
        GIROCONTO            = 'giroconto',            'Giroconto cassa/banca'
        STIPENDI             = 'stipendi',             'Pagamento stipendi'
        ALTRO                = 'altro',                'Altro'

    # Numero di protocollo: MOV-2026-0001. L'anno è quello della data
    # dell'operazione, il progressivo cresce dentro l'anno. Assegnato al primo
    # salvataggio e mai più toccato — è il riferimento con cui si cita un
    # movimento fuori dal sistema.
    anno             = models.PositiveSmallIntegerField(
        null=True, blank=True, editable=False, verbose_name='Anno')
    progressivo      = models.PositiveIntegerField(
        null=True, blank=True, editable=False, verbose_name='Progressivo')
    numero           = models.CharField(
        max_length=20, unique=True, null=True, blank=True, editable=False,
        verbose_name='N° movimento')

    # localdate e non now: su un DateField `timezone.now` restituisce un
    # datetime, che non si può confrontare con le date delle regole.
    data             = models.DateField(default=timezone.localdate, verbose_name='Data')
    causale          = models.CharField(max_length=300, verbose_name='Causale')
    importo          = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Importo (€)',
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    tipo             = models.CharField(max_length=30, choices=Tipo.choices, verbose_name='Tipo')

    conto_dare       = models.ForeignKey(
        ContoContabile, on_delete=models.PROTECT,
        related_name='movimenti_dare', verbose_name='Conto Dare',
    )
    conto_avere      = models.ForeignKey(
        ContoContabile, on_delete=models.PROTECT,
        related_name='movimenti_avere', verbose_name='Conto Avere',
    )

    numero_documento = models.CharField(max_length=100, blank=True, verbose_name='N° documento')

    # Link opzionale ai documenti sorgente
    fattura_attiva   = models.ForeignKey(
        'fatturazione_attiva.Fattura',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='movimenti_prima_nota',
        verbose_name='Fattura cliente',
    )
    fattura_passiva  = models.ForeignKey(
        'acquisti.FatturaPassiva',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='movimenti_prima_nota',
        verbose_name='Fattura fornitore',
    )

    # Valorizzata solo sui righi IVA generati dallo scorporo (vedi signals.py):
    # dice se quell'IVA è stata inclusa in una liquidazione, e quale. Il
    # dettaglio fattura la legge per mostrare "IVA versata"/"IVA da versare"
    # col link diretto, senza bisogno di una relazione a parte.
    liquidazione_iva = models.ForeignKey(
        'LiquidazioneIva',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='movimenti',
        verbose_name='Liquidazione IVA',
    )

    is_automatico    = models.BooleanField(default=False, verbose_name='Generato automaticamente')
    note             = models.TextField(blank=True, verbose_name='Note')

    # Un movimento sbagliato non si cancella e non si corregge: si storna con
    # un movimento uguale e contrario, che resta legato all'originale.
    storna           = models.OneToOneField(
        'self',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='storno',
        verbose_name='Storna il movimento',
    )

    creato_da        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='movimenti_prima_nota_creati',
        verbose_name='Creato da',
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Movimento Prima Nota'
        verbose_name_plural = 'Movimenti Prima Nota'
        ordering            = ['-data', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['anno', 'progressivo'],
                name='movimento_progressivo_unico_per_anno',
            ),
        ]

    def __str__(self):
        return f'{self.numero or "—"} | {self.data:%d/%m/%Y} | {self.causale} | € {self.importo}'

    def get_absolute_url(self):
        return reverse('contabilita:movimento_detail', kwargs={'pk': self.pk})

    # ── Storno ───────────────────────────────────────────────────────────────

    @property
    def is_stornato(self):
        """True se esiste già un movimento che storna questo."""
        return hasattr(self, 'storno')

    @property
    def is_storno(self):
        return self.storna_id is not None

    # ── Validazione dare/avere ───────────────────────────────────────────────

    def _conti(self):
        """
        I due conti, o None se non ancora assegnati.

        Accedere alla FK direttamente solleverebbe RelatedObjectDoesNotExist:
        succede a ogni submit con una tendina vuota o con una scelta scartata
        dal form, cioè proprio quando la validazione deve poter proseguire per
        segnalare il campo mancante.
        """
        return (
            self.conto_dare if self.conto_dare_id else None,
            self.conto_avere if self.conto_avere_id else None,
        )

    def _riferimento_documento(self):
        """
        Data del documento che questo movimento salda, e come chiamarlo.
        Solo per incassi e pagamenti: negli altri tipi la data del movimento
        *è* quella del documento, quindi non c'è niente da confrontare.
        """
        if self.tipo == self.Tipo.INCASSO and self.fattura_attiva_id:
            f = self.fattura_attiva
            return f.data_emissione, f'dell\'emissione della fattura {f.numero}'
        if self.tipo == self.Tipo.PAGAMENTO and self.fattura_passiva_id:
            f = self.fattura_passiva
            return f.data_fattura, f'della fattura fornitore {f.numero_fattura}'
        return None, ''

    def _valida(self):
        """Tutte le regole del movimento, in un messaggio o None."""
        dare, avere = self._conti()
        errore = valida_dare_avere(self.tipo, dare, avere, is_storno=self.is_storno)
        if errore:
            return errore

        data_doc, riferimento = self._riferimento_documento()
        return valida_data_movimento(
            self.data,
            chiusa_fino_al=ImpostazioniContabilita.chiusura(),
            data_documento=data_doc,
            documento=riferimento,
        )

    def clean(self):
        super().clean()
        errore = self._valida()
        if errore:
            raise ValidationError(errore)

    def assegna_numero(self):
        """
        Assegna MOV-<anno>-<progressivo> se il movimento non ce l'ha ancora.

        L'anno è quello della data dell'operazione: un movimento del 2026 porta
        un numero 2026 anche se registrato a gennaio 2027. Il progressivo è il
        massimo dell'anno più uno, letto dentro la transazione che sta
        salvando, così registrandone tre in blocco escono consecutivi.
        """
        data = _come_data(self.data)
        if self.numero or data is None:
            return
        self.anno = data.year
        ultimo = (MovimentoPrimaNota.objects
                  .filter(anno=self.anno)
                  .aggregate(m=models.Max('progressivo'))['m'] or 0)
        self.progressivo = ultimo + 1
        self.numero = f'MOV-{self.anno}-{self.progressivo:04d}'

    def save(self, *args, **kwargs):
        # Le regole si applicano anche fuori dai form (shell, admin, signal,
        # import): è l'unico modo per rendere lo sbaglio impossibile invece
        # che solo improbabile.
        errore = self._valida()
        if errore:
            raise ValidationError(errore)
        self.assegna_numero()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# REGOLE DARE / AVERE
# ─────────────────────────────────────────────────────────────────────────────

_T = MovimentoPrimaNota.Tipo
_C = ContoContabile.Tipo

#: Un conto CUSTODIA (persona che ha in mano contanti/assegni) vale come
#: liquidità aziendale esattamente quanto cassa e banca: è solo "in transito"
#: presso qualcuno invece che in un luogo fisso. Farlo rientrare qui abilita
#: GIROCONTO anche persona↔persona e persona↔cassaforte, senza toccare la
#: matrice né la validazione: sono già generiche su MONETARI.
MONETARI = frozenset({_C.CASSA, _C.BANCA, _C.CUSTODIA})

#: Per ogni tipo di movimento, i tipi di conto ammessi in Dare e in Avere.
#: È la stessa tabella che prima viveva come testo nel pannello dei
#: suggerimenti: qui è un dato, e vincola invece di consigliare.
#:
#: FATTURA_CLIENTE e FATTURA_FORNITORE ammettono anche il conto IVA come
#: contropartita: una fattura genera due movimenti, non uno — un rigo per
#: l'imponibile (Avere/Dare GENERICO) e uno per l'IVA (Avere/Dare
#: IVA_DEBITO/IVA_CREDITO), vedi signals.py. La matrice non sa che sono "due
#: righi di una fattura sola": vede solo due movimenti dello stesso tipo,
#: ciascuno con la propria contropartita ammessa.
REGOLE_DARE_AVERE = {
    _T.FATTURA_CLIENTE:      (frozenset({_C.CLIENTE}),
                              frozenset({_C.GENERICO, _C.IVA_DEBITO})),
    # Storna una fattura cliente: stessa coppia di conti, orientamento
    # opposto — non è lo storno di un movimento specifico (`storna`/
    # `is_storno`), è un documento fiscale a sé, quindi ha una propria voce
    # in tabella invece di bypassare la matrice.
    _T.NOTA_CREDITO_CLIENTE: (frozenset({_C.GENERICO, _C.IVA_DEBITO}),
                              frozenset({_C.CLIENTE})),
    _T.FATTURA_FORNITORE:    (frozenset({_C.GENERICO, _C.IVA_CREDITO}),
                              frozenset({_C.FORNITORE})),
    _T.INCASSO:              (MONETARI,                  frozenset({_C.CLIENTE})),
    _T.PAGAMENTO:            (frozenset({_C.FORNITORE}), MONETARI),
    _T.GIROCONTO:            (MONETARI,                  MONETARI),
    _T.STIPENDI:             (frozenset({_C.GENERICO}),  MONETARI),
    # ALTRO è la via di fuga per i casi non previsti: nessun vincolo di tipo,
    # restano solo le regole generali qui sotto.
}


# ─────────────────────────────────────────────────────────────────────────────
# REGOLE SULLA DATA
# ─────────────────────────────────────────────────────────────────────────────
# `data` è la data dell'operazione, non quella di registrazione: deve poter
# stare nel passato, perché lunedì si registra il bonifico arrivato venerdì e
# la data valuta è quella che determina competenza e riconciliazione. L'ordine
# di inserimento è già crescente da sé, ce l'ha `created_at`.
#
# Quello che non deve poter stare in nessun caso è: nel futuro, in un periodo
# già chiuso, prima del documento che il movimento salda, o così indietro da
# essere un errore di battitura sull'anno.


def data_minima_plausibile(oggi=None):
    """
    Primo giorno dell'anno precedente. Sotto questa soglia una data non è una
    registrazione tardiva ma un anno digitato male.
    """
    oggi = oggi or timezone.localdate()
    return oggi.replace(year=oggi.year - 1, month=1, day=1)


def _come_data(valore):
    """Un `date` da quello che arriva, o None se non è interpretabile."""
    if valore is None or isinstance(valore, date) and not isinstance(valore, datetime):
        return valore
    if isinstance(valore, datetime):
        return timezone.localtime(valore).date() if timezone.is_aware(valore) else valore.date()
    if isinstance(valore, str):
        try:
            return date.fromisoformat(valore[:10])
        except ValueError:
            return None
    return None


def valida_data_movimento(data, *, oggi=None, chiusa_fino_al=None,
                          data_documento=None, documento=''):
    """
    Messaggio d'errore se la data non è registrabile, None se va bene.

    `chiusa_fino_al` e `data_documento` sono opzionali: chi chiama passa
    quello che sa. Il model li ricava da sé, i form li passano per legare
    l'errore al campo giusto.
    """
    if data is None:
        return None

    # La data può arrivare come datetime o come stringa ISO: Django converte
    # al salvataggio, ma l'attributo in memoria resta com'è stato assegnato, e
    # i signal leggono proprio quello. Un confronto fra str e date esploderebbe
    # con un TypeError invece di dire cosa non va.
    data = _come_data(data)
    if data is None:
        return None

    oggi = oggi or timezone.localdate()

    if data > oggi:
        return (
            f'La data del movimento è nel futuro ({data:%d/%m/%Y}). '
            'Si registra un\'operazione avvenuta, non una prevista.'
        )

    minima = data_minima_plausibile(oggi)
    if data < minima:
        return (
            f'La data {data:%d/%m/%Y} è precedente al {minima:%d/%m/%Y}: '
            'controlla l\'anno, sembra un errore di battitura.'
        )

    if chiusa_fino_al and data <= chiusa_fino_al:
        return (
            f'La contabilità è chiusa fino al {chiusa_fino_al:%d/%m/%Y}: '
            f'non si registrano movimenti al {data:%d/%m/%Y}. '
            'Usa una data successiva, o fatti spostare la chiusura.'
        )

    data_documento = _come_data(data_documento)
    if data_documento and data < data_documento:
        rif = f' {documento}' if documento else ''
        return (
            f'Il movimento è datato {data:%d/%m/%Y}, prima{rif} '
            f'del {data_documento:%d/%m/%Y}: non si salda un documento '
            'che ancora non esiste.'
        )

    return None


def _elenco(tipi):
    etichette = dict(ContoContabile.Tipo.choices)
    return ' o '.join(etichette[t] for t in sorted(tipi))


def valida_dare_avere(tipo, conto_dare, conto_avere, is_storno=False):
    """
    Messaggio d'errore se la combinazione tipo/dare/avere è incoerente,
    None se il movimento è registrabile.

    Vive fuori dal model perché serve anche al form (per filtrare le tendine
    prima che l'utente sbagli) e ai controlli di quadratura, che la applicano
    ai movimenti storici registrati prima della regola.

    Uno storno viola la matrice per costruzione — è il movimento contrario di
    uno che la rispetta — quindi la salta: la sua correttezza è garantita dal
    fatto che i conti li copia dall'originale, non li sceglie nessuno.
    """
    if conto_dare is None or conto_avere is None:
        return None  # campo obbligatorio mancante: lo segnala il form

    if conto_dare == conto_avere:
        return 'Il conto Dare e il conto Avere non possono essere lo stesso conto.'

    regola = None if is_storno else REGOLE_DARE_AVERE.get(tipo)
    if regola is None:
        return None

    ammessi_dare, ammessi_avere = regola
    etichetta = dict(MovimentoPrimaNota.Tipo.choices).get(tipo, tipo)

    # L'inversione dei due lati è l'errore tipico: vale la pena riconoscerla e
    # dirlo, invece di lasciare l'utente davanti a un generico "non ammesso".
    if (conto_dare.tipo in ammessi_avere and conto_avere.tipo in ammessi_dare
            and ammessi_dare != ammessi_avere):
        return (
            f'Dare e Avere sono invertiti. In un movimento di tipo "{etichetta}" '
            f'va in Dare il conto {_elenco(ammessi_dare)} ({conto_avere.nome}) '
            f'e in Avere il conto {_elenco(ammessi_avere)} ({conto_dare.nome}).'
        )

    if conto_dare.tipo not in ammessi_dare:
        return (
            f'In un movimento di tipo "{etichetta}" il conto Dare dev\'essere di tipo '
            f'{_elenco(ammessi_dare)}: "{conto_dare.nome}" è un conto '
            f'{conto_dare.get_tipo_display().lower()}.'
        )

    if conto_avere.tipo not in ammessi_avere:
        return (
            f'In un movimento di tipo "{etichetta}" il conto Avere dev\'essere di tipo '
            f'{_elenco(ammessi_avere)}: "{conto_avere.nome}" è un conto '
            f'{conto_avere.get_tipo_display().lower()}.'
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PASSAGGIO CASSA
# ─────────────────────────────────────────────────────────────────────────────

class PassaggioCassa(AllegatiMixin, models.Model):
    """
    Un passaggio di contanti/assegni da un conto di custodia a un altro:
    tecnico → cassiere, cassiere → cassaforte, cassaforte → banca, o fra due
    persone qualsiasi. È un oggetto di per sé, non solo una riga di prima
    nota — l'amministrazione deve poterlo consultare come evento (chi, a chi,
    quanto, quando, con che pezza d'appoggio), non solo come dare/avere.

    Alla creazione genera in automatico il `MovimentoPrimaNota` di tipo
    GIROCONTO corrispondente (vedi `contabilita/signals.py`), stesso
    meccanismo già usato per `Fattura` e `FatturaPassiva`: qui vive il fatto
    di dominio, il movimento è la sua ombra contabile.
    """

    class Forma(models.TextChoices):
        CONTANTI = 'contanti', 'Contanti'
        ASSEGNO  = 'assegno',  'Assegno'

    data       = models.DateField(default=timezone.localdate, verbose_name='Data')
    da_conto   = models.ForeignKey(
        ContoContabile, on_delete=models.PROTECT,
        related_name='passaggi_consegnati', verbose_name='Chi consegna',
    )
    a_conto    = models.ForeignKey(
        ContoContabile, on_delete=models.PROTECT,
        related_name='passaggi_ricevuti', verbose_name='Chi riceve',
    )
    importo    = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Importo (€)',
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    forma      = models.CharField(
        max_length=10, choices=Forma.choices, default=Forma.CONTANTI,
        verbose_name='Forma',
    )
    causale    = models.CharField(max_length=300, verbose_name='Causale')
    note       = models.TextField(blank=True, verbose_name='Note')

    # Valorizzato dal signal appena il movimento viene creato: SET_NULL e non
    # CASCADE perché uno storno in prima nota non deve far sparire il
    # passaggio che lo ha originato, resta l'evento consultabile.
    movimento  = models.OneToOneField(
        MovimentoPrimaNota, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='passaggio_cassa', verbose_name='Movimento generato',
    )

    creato_da  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='passaggi_cassa_creati',
        verbose_name='Registrato da',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Passaggio di cassa'
        verbose_name_plural  = 'Passaggi di cassa'
        ordering             = ['-data', '-created_at']

    def __str__(self):
        return f'{self.da_conto.nome} → {self.a_conto.nome} — € {self.importo}'

    def get_absolute_url(self):
        return reverse('contabilita:passaggio_cassa_detail', kwargs={'pk': self.pk})

    def clean(self):
        if self.da_conto_id and self.a_conto_id and self.da_conto_id == self.a_conto_id:
            raise ValidationError('Chi consegna e chi riceve non possono essere lo stesso conto.')
        for campo, conto in (('da_conto', self.da_conto if self.da_conto_id else None),
                             ('a_conto', self.a_conto if self.a_conto_id else None)):
            if conto and conto.tipo not in MONETARI:
                raise ValidationError({
                    campo: f'"{conto.nome}" è un conto {conto.get_tipo_display().lower()}: '
                           'un passaggio di cassa si fa solo fra cassa, banca o persona.',
                })
