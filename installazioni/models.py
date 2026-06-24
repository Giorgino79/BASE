from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Max

from core.mixins.model_mixins import AllegatiMixin, QRCodeMixin


def _next_numero_installazione():
    anno = timezone.now().year
    prefix = f"INS-{anno}-"
    ultimo = Installazione.objects.filter(numero__startswith=prefix).order_by("numero").last()
    if ultimo:
        try:
            n = int(ultimo.numero.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


class Installazione(AllegatiMixin, models.Model):

    numero = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Numero")

    filiale = models.ForeignKey(
        "anagrafica.Filiale", on_delete=models.PROTECT,
        null=True, blank=True, related_name="installazioni", verbose_name="Sede cliente",
    )
    privato = models.ForeignKey(
        "anagrafica.Privato", on_delete=models.PROTECT,
        null=True, blank=True, related_name="installazioni", verbose_name="Cliente privato",
    )
    servizio = models.ForeignKey(
        "servizi.Servizio", on_delete=models.PROTECT,
        limit_choices_to={"richiede_installazione": True},
        related_name="installazioni", verbose_name="Tipo installazione",
    )
    prodotto_principale = models.ForeignKey(
        "magazzino.Prodotto", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="installazioni", verbose_name="Prodotto principale",
    )
    data_installazione = models.DateField(
        verbose_name="Data installazione", default=timezone.localdate,
    )
    attiva = models.BooleanField(default=True, verbose_name="Attiva")
    note = models.TextField(blank=True, verbose_name="Note")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="installazioni_create",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Installazione"
        verbose_name_plural = "Installazioni"
        ordering = ["-data_installazione", "-created_at"]

    def __str__(self):
        return f"{self.numero} — {self.cliente_display}"

    def get_absolute_url(self):
        return reverse("installazioni:installazione_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = _next_numero_installazione()
        super().save(*args, **kwargs)

    def clean(self):
        if not self.filiale and not self.privato:
            raise ValidationError("Seleziona una sede cliente o un cliente privato.")
        if self.filiale and self.privato:
            raise ValidationError("Seleziona solo una sede oppure un privato, non entrambi.")

    @property
    def cliente_display(self):
        if self.filiale:
            return f"{self.filiale.cliente} — {self.filiale.nome}"
        if self.privato:
            return str(self.privato)
        return "—"

    @property
    def n_postazioni(self):
        return self.postazioni.count()


class Postazione(AllegatiMixin, QRCodeMixin, models.Model):

    installazione = models.ForeignKey(
        Installazione, on_delete=models.CASCADE,
        related_name="postazioni", verbose_name="Installazione",
    )
    numero = models.PositiveSmallIntegerField(
        verbose_name="N° postazione",
        help_text="Lascia vuoto: verrà assegnato automaticamente in sequenza",
    )
    descrizione_luogo = models.TextField(
        blank=True, verbose_name="Descrizione luogo",
        help_text="Descrivi la posizione esatta (es. 'angolo nord-est magazzino, vicino al bancale B')",
    )
    ha_cartello = models.BooleanField(
        default=True, verbose_name="Ha cartello",
        help_text="Deseleziona se non è possibile apporre un cartello segnaletico",
    )
    numero_cartello = models.CharField(
        max_length=50, blank=True, verbose_name="N° cartello",
        help_text="Numero/codice del cartello segnaletico applicato",
    )
    prodotto = models.ForeignKey(
        "magazzino.Prodotto", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="postazioni", verbose_name="Prodotto",
    )
    quantita = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Quantità",
    )
    note = models.TextField(blank=True, verbose_name="Note")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Postazione"
        verbose_name_plural = "Postazioni"
        ordering = ["numero"]
        unique_together = [("installazione", "numero")]

    def __str__(self):
        return f"{self.installazione.numero} — P{self.numero:02d}"

    def get_absolute_url(self):
        return reverse("installazioni:postazione_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.pk and not self.numero:
            last = (
                Postazione.objects
                .filter(installazione=self.installazione)
                .aggregate(Max("numero"))["numero__max"] or 0
            )
            self.numero = last + 1
        super().save(*args, **kwargs)

    @property
    def label(self):
        return f"Postazione {self.numero:02d}"


class InterventoInstallazione(models.Model):

    installazione = models.ForeignKey(
        Installazione, on_delete=models.CASCADE,
        related_name="interventi", verbose_name="Installazione",
    )
    data_intervento = models.DateField(
        verbose_name="Data intervento", default=timezone.localdate,
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="interventi_installazioni", verbose_name="Tecnico",
    )
    prodotto = models.ForeignKey(
        "magazzino.Prodotto", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="interventi_installazioni", verbose_name="Prodotto usato",
    )
    quantita_prodotto = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        verbose_name="Quantità prodotto",
    )
    note = models.TextField(blank=True, verbose_name="Note intervento")
    ods = models.ForeignKey(
        "servizi.ODS", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="interventi_installazioni",
        verbose_name="ODS collegato",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="interventi_installazioni_creati",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intervento"
        verbose_name_plural = "Interventi"
        ordering = ["-data_intervento", "-created_at"]

    def __str__(self):
        return f"{self.installazione.numero} — {self.data_intervento:%d/%m/%Y}"

    def get_absolute_url(self):
        return reverse("installazioni:intervento_detail", kwargs={"pk": self.pk})


class RiscontroPostazione(models.Model):

    class Esito(models.TextChoices):
        VUOTA       = "vuota",       "Vuota / nessuna attività"
        INNESCATA   = "innescata",   "Innescata / esca consumata"
        RODITORI    = "roditori",    "Roditori trovati"
        INSETTI     = "insetti",     "Insetti trovati"
        DANNEGGIATA = "danneggiata", "Postazione danneggiata"
        ASSENTE     = "assente",     "Postazione assente / non trovata"

    intervento = models.ForeignKey(
        InterventoInstallazione, on_delete=models.CASCADE,
        related_name="riscontri", verbose_name="Intervento",
    )
    postazione = models.ForeignKey(
        Postazione, on_delete=models.CASCADE,
        related_name="riscontri", verbose_name="Postazione",
    )
    esito = models.CharField(
        max_length=20, choices=Esito.choices, verbose_name="Esito",
    )
    note = models.CharField(max_length=300, blank=True, verbose_name="Note")

    class Meta:
        verbose_name = "Riscontro postazione"
        verbose_name_plural = "Riscontri postazione"
        unique_together = [("intervento", "postazione")]
        ordering = ["postazione__numero"]

    def __str__(self):
        return f"{self.postazione} — {self.get_esito_display()}"
