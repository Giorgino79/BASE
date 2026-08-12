from datetime import date, datetime
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
        CLIENTE    = 'cliente',    'Cliente'
        FORNITORE  = 'fornitore',  'Fornitore'
        CASSA      = 'cassa',      'Cassa'
        BANCA      = 'banca',      'Banca'
        GENERICO   = 'generico',   'Generico'

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


class MovimentoPrimaNota(AllegatiMixin, models.Model):
    """
    Singola riga della prima nota: un dare, un avere, un importo.
    """

    class Tipo(models.TextChoices):
        FATTURA_CLIENTE    = 'fattura_cliente',    'Fattura cliente'
        FATTURA_FORNITORE  = 'fattura_fornitore',  'Fattura fornitore'
        INCASSO            = 'incasso',            'Incasso da cliente'
        PAGAMENTO          = 'pagamento',          'Pagamento a fornitore'
        GIROCONTO          = 'giroconto',          'Giroconto cassa/banca'
        STIPENDI           = 'stipendi',           'Pagamento stipendi'
        ALTRO              = 'altro',              'Altro'

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

MONETARI = frozenset({_C.CASSA, _C.BANCA})

#: Per ogni tipo di movimento, i tipi di conto ammessi in Dare e in Avere.
#: È la stessa tabella che prima viveva come testo nel pannello dei
#: suggerimenti: qui è un dato, e vincola invece di consigliare.
REGOLE_DARE_AVERE = {
    _T.FATTURA_CLIENTE:   (frozenset({_C.CLIENTE}),   frozenset({_C.GENERICO})),
    _T.FATTURA_FORNITORE: (frozenset({_C.GENERICO}),  frozenset({_C.FORNITORE})),
    _T.INCASSO:           (MONETARI,                  frozenset({_C.CLIENTE})),
    _T.PAGAMENTO:         (frozenset({_C.FORNITORE}), MONETARI),
    _T.GIROCONTO:         (MONETARI,                  MONETARI),
    _T.STIPENDI:          (frozenset({_C.GENERICO}),  MONETARI),
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
