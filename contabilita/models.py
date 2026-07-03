from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


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


class MovimentoPrimaNota(models.Model):
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
    importo          = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Importo (€)')
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
