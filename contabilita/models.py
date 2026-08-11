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

    data             = models.DateField(default=timezone.now, verbose_name='Data')
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

    def __str__(self):
        return f'{self.data:%d/%m/%Y} | {self.causale} | € {self.importo}'

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

    def clean(self):
        super().clean()
        dare, avere = self._conti()
        errore = valida_dare_avere(self.tipo, dare, avere, is_storno=self.is_storno)
        if errore:
            raise ValidationError(errore)

    def save(self, *args, **kwargs):
        # La regola dare/avere si applica anche fuori dai form (shell, admin,
        # signal, import): è l'unico modo per rendere l'inversione impossibile
        # invece che solo improbabile.
        dare, avere = self._conti()
        errore = valida_dare_avere(self.tipo, dare, avere, is_storno=self.is_storno)
        if errore:
            raise ValidationError(errore)
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
