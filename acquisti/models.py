from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from core.mixins.model_mixins import AllegatiMixin


def _next_numero_ordine():
    anno = timezone.now().year
    prefix = f"ODA-{anno}-"
    ultimo = (
        OrdineAcquisto.objects.filter(numero_ordine__startswith=prefix)
        .order_by("numero_ordine")
        .last()
    )
    if ultimo:
        try:
            n = int(ultimo.numero_ordine.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


class OrdineAcquisto(AllegatiMixin, models.Model):

    class Stato(models.TextChoices):
        BOZZA = "bozza", "Bozza"
        INVIATO = "inviato", "Inviato al fornitore"
        RICEVUTO_PARZ = "ricevuto_parz", "Ricevuto parzialmente"
        RICEVUTO = "ricevuto", "Ricevuto"
        FATTURATO = "fatturato", "Fatturato"
        PAGATO = "pagato", "Pagato"
        ANNULLATO = "annullato", "Annullato"

    numero_ordine = models.CharField(max_length=50, unique=True, blank=True)
    data_ordine = models.DateField(default=timezone.localdate)
    data_consegna_richiesta = models.DateField(null=True, blank=True)
    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.PROTECT,
        related_name="ordini_acquisto",
    )
    stato = models.CharField(max_length=20, choices=Stato.choices, default=Stato.BOZZA)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordini_acquisto_creati",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ordine di Acquisto"
        verbose_name_plural = "Ordini di Acquisto"
        ordering = ["-data_ordine", "-created_at"]

    def __str__(self):
        return f"{self.numero_ordine} — {self.fornitore}"

    def get_absolute_url(self):
        return reverse("acquisti:ordine_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.numero_ordine:
            self.numero_ordine = _next_numero_ordine()
        super().save(*args, **kwargs)

    @property
    def totale_imponibile(self):
        return sum(r.imponibile for r in self.righe.all())

    @property
    def totale(self):
        return self.totale_imponibile

    @property
    def totale_iva(self):
        return sum(r.importo_iva for r in self.righe.all())

    @property
    def totale_ivato(self):
        return (self.totale_imponibile + self.totale_iva).quantize(Decimal("0.01"))

    @property
    def is_completamente_ricevuto(self):
        righe = list(self.righe.all())
        if not righe:
            return False
        return all(r.quantita_ricevuta >= r.quantita_ordinata for r in righe)


class RigaOrdine(models.Model):
    ordine = models.ForeignKey(
        OrdineAcquisto, on_delete=models.CASCADE, related_name="righe"
    )
    prodotto = models.ForeignKey(
        "magazzino.Prodotto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="righe_ordine",
    )
    descrizione = models.CharField(
        max_length=300,
        blank=True,
        help_text="Descrizione articolo (se prodotto non selezionato)",
    )
    unita_misura = models.CharField(max_length=20, blank=True)
    quantita_ordinata = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("1.000")
    )
    quantita_ricevuta = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    prezzo_unitario = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0.0000")
    )
    aliquota_iva = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("22.00"),
        verbose_name="IVA %",
    )
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Riga Ordine"
        verbose_name_plural = "Righe Ordine"
        ordering = ["pk"]

    def __str__(self):
        nome = str(self.prodotto) if self.prodotto else self.descrizione
        return f"{nome} x{self.quantita_ordinata}"

    @property
    def imponibile(self):
        return (self.quantita_ordinata * self.prezzo_unitario).quantize(Decimal("0.01"))

    @property
    def importo_iva(self):
        return (self.imponibile * self.aliquota_iva / 100).quantize(Decimal("0.01"))

    @property
    def totale_riga(self):
        return (self.imponibile + self.importo_iva).quantize(Decimal("0.01"))

    @property
    def da_ricevere(self):
        return max(Decimal("0"), self.quantita_ordinata - self.quantita_ricevuta)


class FatturaPassiva(models.Model):

    class StatoPagamento(models.TextChoices):
        DA_PAGARE = "da_pagare", "Da pagare"
        PAGATA = "pagata", "Pagata"
        ANNULLATA = "annullata", "Annullata"

    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.PROTECT,
        related_name="fatture_passive",
    )
    ordini = models.ManyToManyField(
        OrdineAcquisto,
        blank=True,
        related_name="fatture",
        verbose_name="Ordini collegati",
    )
    numero_fattura = models.CharField(max_length=50)
    data_fattura = models.DateField()
    data_scadenza = models.DateField(null=True, blank=True)
    imponibile = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    aliquota_iva = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("22.00")
    )
    importo_iva = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    totale = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    file_fattura = models.FileField(upload_to="fatture_passive/%Y/", null=True, blank=True)
    stato_pagamento = models.CharField(
        max_length=20,
        choices=StatoPagamento.choices,
        default=StatoPagamento.DA_PAGARE,
    )
    data_pagamento = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fatture_passive_create",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fattura Passiva"
        verbose_name_plural = "Fatture Passive"
        ordering = ["-data_fattura"]
        unique_together = [("fornitore", "numero_fattura")]

    def __str__(self):
        return f"Ft {self.numero_fattura} — {self.fornitore} ({self.data_fattura:%d/%m/%Y})"

    def get_absolute_url(self):
        return reverse("acquisti:fattura_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.imponibile and self.aliquota_iva:
            self.importo_iva = (self.imponibile * self.aliquota_iva / 100).quantize(
                Decimal("0.01")
            )
            self.totale = (self.imponibile + self.importo_iva).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
