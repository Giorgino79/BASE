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

    class Stato(models.TextChoices):
        IN_CORSO   = "in_corso",   "In corso"
        COMPLETATA = "completata", "Completata"

    numero = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Numero")

    stato = models.CharField(
        max_length=20, choices=Stato.choices, default=Stato.IN_CORSO,
        verbose_name="Stato",
    )
    data_completamento = models.DateField(
        null=True, blank=True, verbose_name="Data completamento",
    )
    chiusa_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="installazioni_chiuse",
        verbose_name="Chiusa da",
    )

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

    ods_creato = models.OneToOneField(
        "servizi.ODS", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="installazione_collegata",
        verbose_name="ODS creato",
    )

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

    @property
    def is_completata(self):
        return self.stato == self.Stato.COMPLETATA

    def chiudi(self, user):
        self.stato = self.Stato.COMPLETATA
        self.data_completamento = timezone.localdate()
        self.chiusa_da = user
        self.save(update_fields=["stato", "data_completamento", "chiusa_da", "updated_at"])

    def riapri(self):
        self.stato = self.Stato.IN_CORSO
        self.data_completamento = None
        self.chiusa_da = None
        self.save(update_fields=["stato", "data_completamento", "chiusa_da", "updated_at"])


class Planimetria(models.Model):

    installazione = models.ForeignKey(
        Installazione, on_delete=models.CASCADE,
        related_name="planimetrie", verbose_name="Installazione",
    )
    titolo = models.CharField(
        max_length=100, blank=True, verbose_name="Titolo",
        help_text="Es. 'Piano terra', 'Magazzino', 'Cucina'",
    )
    immagine = models.FileField(
        upload_to="planimetrie/%Y/%m/", verbose_name="Immagine planimetria",
        help_text="JPG, PNG o HEIC (foto da smartphone)",
    )
    note = models.TextField(blank=True, verbose_name="Note")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="planimetrie_create",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Planimetria"
        verbose_name_plural = "Planimetrie"
        ordering = ["titolo", "created_at"]

    def __str__(self):
        return self.titolo or f"Planimetria #{self.pk}"

    def get_absolute_url(self):
        return reverse("installazioni:planimetria_detail", kwargs={"pk": self.pk})

    @property
    def n_postazioni_posizionate(self):
        return self.postazioni.filter(pos_x__isnull=False, pos_y__isnull=False).count()

    def generate_annotated_image_bytes(self):
        """
        Restituisce i bytes PNG della planimetria con i pin delle postazioni
        posizionate disegnati sopra (cerchio numerato). Usato per il report PDF.
        Solleva eccezione se il file non è un'immagine decodificabile (es. HEIC
        senza supporto) — il chiamante deve gestire il fallback.
        """
        from PIL import Image, ImageDraw, ImageFont
        import io

        self.immagine.open()
        try:
            img = Image.open(self.immagine)
            img.load()
            img = img.convert("RGB")
        finally:
            self.immagine.close()

        draw = ImageDraw.Draw(img)
        w, h = img.size
        radius = max(16, min(w, h) // 35)

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(radius * 1.1))
        except Exception:
            font = ImageFont.load_default(size=int(radius * 1.1))

        for p in self.postazioni.filter(pos_x__isnull=False, pos_y__isnull=False):
            cx = float(p.pos_x) / 100 * w
            cy = float(p.pos_y) / 100 * h
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=(37, 99, 235), outline=(255, 255, 255), width=max(2, radius // 6),
            )
            label = str(p.numero)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), label, fill=(255, 255, 255), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


class Postazione(AllegatiMixin, QRCodeMixin, models.Model):

    installazione = models.ForeignKey(
        Installazione, on_delete=models.CASCADE,
        related_name="postazioni", verbose_name="Installazione",
    )
    numero = models.PositiveSmallIntegerField(
        verbose_name="N° postazione",
        help_text="Lascia vuoto: verrà assegnato automaticamente in sequenza",
    )
    planimetria = models.ForeignKey(
        Planimetria, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="postazioni", verbose_name="Planimetria",
    )
    pos_x = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Posizione X (%)",
        help_text="Percentuale orizzontale sulla planimetria (0-100)",
    )
    pos_y = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Posizione Y (%)",
        help_text="Percentuale verticale sulla planimetria (0-100)",
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

    @property
    def is_pinned(self):
        return self.planimetria_id is not None and self.pos_x is not None and self.pos_y is not None


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
