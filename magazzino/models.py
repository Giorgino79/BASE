from django.db import models
from django.db.models import F
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
from core.mixins.model_mixins import AllegatiMixin


class Categoria(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    descrizione = models.TextField(blank=True)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorie"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Prodotto(AllegatiMixin, models.Model):

    class UnitaMisura(models.TextChoices):
        PEZZO = "pz", "Pezzo (pz)"
        CONFEZIONE = "conf", "Confezione"
        KILOGRAMMO = "kg", "Chilogrammo (kg)"
        GRAMMO = "gr", "Grammo (gr)"
        LITRO = "lt", "Litro (lt)"
        MILLILITRO = "ml", "Millilitro (ml)"

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="prodotti",
    )
    fornitore_principale = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prodotti_magazzino",
    )
    nome_prodotto = models.CharField(max_length=200)
    codice_interno = models.CharField(max_length=50, blank=True, unique=True, null=True)
    codice_fornitore = models.CharField(max_length=50, blank=True)
    descrizione = models.TextField(blank=True)
    unita_misura = models.CharField(
        max_length=10, choices=UnitaMisura.choices, default=UnitaMisura.PEZZO
    )
    quantita_per_confezione = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Quantità unitaria contenuta in ogni confezione (es: 1000 esche, 10 lt)",
    )
    formato_confezione = models.CharField(
        max_length=100,
        blank=True,
        help_text="Descrizione formato (es: conf. da 1000 esche, tanica 10L)",
    )
    is_biocida = models.BooleanField(
        default=False,
        verbose_name="Biocida",
        help_text="Il prodotto è un biocida registrato",
    )
    principio_attivo = models.CharField(max_length=200, blank=True)
    numero_registrazione = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numero di registrazione ministeriale del biocida",
    )
    attivo = models.BooleanField(default=True)
    scorta_minima = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Scorta minima",
        help_text="Soglia sotto cui il prodotto compare nell'avviso scorte basse",
    )
    note_interne = models.TextField(blank=True)
    immagine = models.ImageField(
        upload_to="magazzino/prodotti/", null=True, blank=True
    )
    scheda_tecnica = models.FileField(
        upload_to="magazzino/schede_tecniche/", null=True, blank=True, verbose_name="Scheda tecnica"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prodotto"
        verbose_name_plural = "Prodotti"
        ordering = ["nome_prodotto"]
        indexes = [
            models.Index(fields=["codice_interno"]),
            models.Index(fields=["categoria", "attivo"]),
        ]

    def __str__(self):
        if self.codice_interno:
            return f"{self.codice_interno} — {self.nome_prodotto}"
        return self.nome_prodotto

    def get_absolute_url(self):
        return reverse("magazzino:prodotto_detail", kwargs={"pk": self.pk})


class Ricezione(AllegatiMixin, models.Model):
    """DDT / bolla di consegna — registra l'arrivo fisico della merce."""

    numero_ddt = models.CharField(max_length=50, blank=True)
    data_ricezione = models.DateField()
    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.PROTECT,
        related_name="ricezioni",
    )
    ordine = models.ForeignKey(
        "acquisti.OrdineAcquisto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ricezioni",
        verbose_name="ODA di riferimento",
    )
    stabilimento = models.ForeignKey(
        "cespiti.Stabilimento",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="ricezioni_magazzino",
        verbose_name="Stabilimento destinatario",
    )
    mezzo = models.ForeignKey(
        "cespiti.Automezzo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="ricezioni_mezzo",
        verbose_name="Mezzo destinatario",
    )
    bolla_firmata = models.FileField(
        upload_to="magazzino/bolle_firmate/",
        null=True, blank=True,
        verbose_name="Bolla firmata",
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ricezioni_create",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ricezione"
        verbose_name_plural = "Ricezioni"
        ordering = ["-data_ricezione", "-created_at"]

    def __str__(self):
        ddt = f" DDT {self.numero_ddt}" if self.numero_ddt else ""
        return f"Ricezione {self.data_ricezione:%d/%m/%Y}{ddt} — {self.fornitore}"

    def get_absolute_url(self):
        return reverse("magazzino:ricezione_detail", kwargs={"pk": self.pk})


class RigaRicezione(models.Model):
    ricezione = models.ForeignKey(
        Ricezione, on_delete=models.CASCADE, related_name="righe"
    )
    riga_ordine = models.ForeignKey(
        "acquisti.RigaOrdine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="righe_ricezione",
        verbose_name="Riga ODA",
    )
    prodotto = models.ForeignKey(
        Prodotto,
        on_delete=models.PROTECT,
        related_name="righe_ricezione",
    )
    nr_colli = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nr. colli ricevuti")
    quantita_ricevuta = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    prezzo_unitario = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0.0000"), blank=True
    )
    numero_lotto = models.CharField(max_length=100, blank=True)
    data_scadenza_lotto = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Riga Ricezione"
        verbose_name_plural = "Righe Ricezione"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.prodotto} x{self.quantita_ricevuta}"

    @property
    def imponibile(self):
        return (self.quantita_ricevuta * self.prezzo_unitario).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        if self.pk:
            old_qty = RigaRicezione.objects.filter(pk=self.pk).values_list(
                "quantita_ricevuta", flat=True
            ).first() or Decimal("0")
        else:
            old_qty = Decimal("0")

        super().save(*args, **kwargs)

        if self.riga_ordine_id:
            self._aggiorna_riga_ordine()

        delta = self.quantita_ricevuta - old_qty
        if delta:
            rec = Ricezione.objects.filter(pk=self.ricezione_id).values("stabilimento_id", "mezzo_id").first()
            if rec and rec["mezzo_id"]:
                sm, _ = ScortaMezzo.objects.get_or_create(
                    mezzo_id=rec["mezzo_id"], prodotto_id=self.prodotto_id,
                    defaults={"quantita": Decimal("0")},
                )
                ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") + delta)
            elif rec and rec["stabilimento_id"]:
                ScortaStabilimento.aggiungi(self.prodotto_id, rec["stabilimento_id"], delta)

    def delete(self, *args, **kwargs):
        prodotto_id = self.prodotto_id
        qty = self.quantita_ricevuta
        rec = Ricezione.objects.filter(pk=self.ricezione_id).values("stabilimento_id", "mezzo_id").first()
        super().delete(*args, **kwargs)
        if qty and rec:
            if rec["mezzo_id"]:
                ScortaMezzo.objects.filter(
                    mezzo_id=rec["mezzo_id"], prodotto_id=prodotto_id
                ).update(quantita=F("quantita") - qty)
            elif rec["stabilimento_id"]:
                ScortaStabilimento.aggiungi(prodotto_id, rec["stabilimento_id"], -qty)

    def _aggiorna_riga_ordine(self):
        from acquisti.models import RigaOrdine, OrdineAcquisto
        from django.db.models import Sum
        riga = RigaOrdine.objects.filter(pk=self.riga_ordine_id).first()
        if not riga:
            return
        totale_ricevuto = (
            RigaRicezione.objects.filter(riga_ordine=riga)
            .aggregate(tot=Sum("quantita_ricevuta"))["tot"]
            or Decimal("0")
        )
        # Rettifica la quantità ordinata per allinearla a quanto effettivamente ricevuto
        update_fields = ["quantita_ricevuta"]
        if totale_ricevuto != riga.quantita_ordinata:
            riga.quantita_ordinata = totale_ricevuto
            update_fields.append("quantita_ordinata")
        riga.quantita_ricevuta = totale_ricevuto
        riga.save(update_fields=update_fields)
        # Chiude sempre l'ODA come ricevuto, indipendentemente dalla quantità
        ordine = riga.ordine
        if ordine.stato not in (OrdineAcquisto.Stato.FATTURATO, OrdineAcquisto.Stato.PAGATO):
            ordine.stato = OrdineAcquisto.Stato.RICEVUTO
            ordine.save(update_fields=["stato"])


# ── SCORTE ────────────────────────────────────────────────────

class ScortaStabilimento(models.Model):
    """Giacenza di un prodotto nel magazzino di uno stabilimento."""
    stabilimento = models.ForeignKey(
        "cespiti.Stabilimento",
        on_delete=models.CASCADE,
        related_name="scorte_prodotti",
    )
    prodotto = models.ForeignKey(
        Prodotto, on_delete=models.CASCADE, related_name="scorte_stabilimenti"
    )
    quantita = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scorta Stabilimento"
        verbose_name_plural = "Scorte Stabilimenti"
        unique_together = [("stabilimento", "prodotto")]
        ordering = ["stabilimento", "prodotto__nome_prodotto"]

    def __str__(self):
        return f"{self.stabilimento} — {self.prodotto}: {self.quantita}"

    @classmethod
    def aggiungi(cls, prodotto_id, stabilimento_id, delta):
        if not stabilimento_id:
            return
        from django.db.models import F
        scorta, _ = cls.objects.get_or_create(
            prodotto_id=prodotto_id,
            stabilimento_id=stabilimento_id,
            defaults={"quantita": Decimal("0")},
        )
        cls.objects.filter(pk=scorta.pk).update(quantita=F("quantita") + delta)


class CaricoMezzo(AllegatiMixin, models.Model):
    """Operazione di carico (da magazzino a mezzo) o scarico (da mezzo a magazzino)."""

    class Tipo(models.TextChoices):
        CARICO = "carico", "Carico mezzo"
        SCARICO = "scarico", "Scarico mezzo"

    mezzo = models.ForeignKey(
        "cespiti.Automezzo", on_delete=models.CASCADE, related_name="carichi_magazzino"
    )
    stabilimento = models.ForeignKey(
        "cespiti.Stabilimento",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="carichi_mezzo",
        verbose_name="Stabilimento",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    data = models.DateField(auto_now_add=True)
    operatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="carichi_mezzo",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Carico/Scarico Mezzo"
        verbose_name_plural = "Carichi/Scarichi Mezzo"
        ordering = ["-data", "-created_at"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.mezzo} — {self.data:%d/%m/%Y}"

    def get_absolute_url(self):
        return reverse("magazzino:carico_mezzo_detail", kwargs={"pk": self.pk})


class RigaCaricoMezzo(models.Model):
    carico = models.ForeignKey(
        CaricoMezzo, on_delete=models.CASCADE, related_name="righe"
    )
    prodotto = models.ForeignKey(
        Prodotto, on_delete=models.PROTECT, related_name="righe_carico_mezzo"
    )
    quantita = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        verbose_name = "Riga Carico Mezzo"
        verbose_name_plural = "Righe Carico Mezzo"

    def __str__(self):
        return f"{self.prodotto} × {self.quantita}"


class ScortaMezzo(models.Model):
    """Giacenza di un prodotto a bordo di un mezzo specifico."""
    mezzo = models.ForeignKey(
        "cespiti.Automezzo", on_delete=models.CASCADE, related_name="scorte_magazzino"
    )
    prodotto = models.ForeignKey(
        Prodotto, on_delete=models.CASCADE, related_name="scorte_mezzo"
    )
    quantita = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scorta Mezzo"
        verbose_name_plural = "Scorte Mezzo"
        unique_together = [("mezzo", "prodotto")]
        ordering = ["mezzo", "prodotto__nome_prodotto"]

    def __str__(self):
        return f"{self.mezzo} — {self.prodotto}: {self.quantita}"
