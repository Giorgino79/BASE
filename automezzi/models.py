from django.db import models
from django.conf import settings
from core.mixins.model_mixins import AllegatiMixin


# ============================================================
# UPLOAD PATHS
# ============================================================

def libretto_upload_path(instance, filename):
    return f"automezzi/libretti/{instance.targa}/{filename}"


def assicurazione_upload_path(instance, filename):
    return f"automezzi/assicurazioni/{instance.targa}/{filename}"


def scontrino_upload_path(instance, filename):
    return f"automezzi/rifornimenti/{instance.automezzo.targa}/{filename}"


def allegati_manutenzione_path(instance, filename):
    return f"automezzi/manutenzioni/{filename}"


def allegato_evento_path(instance, filename):
    return f"automezzi/eventi/{filename}"


# ============================================================
# AUTOMEZZI
# ============================================================

class Automezzo(AllegatiMixin, models.Model):
    numero_mezzo = models.IntegerField(blank=True, null=True)
    targa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modello = models.CharField(max_length=50)
    anno_immatricolazione = models.PositiveIntegerField()
    chilometri_attuali = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    disponibile = models.BooleanField(default=True)
    bloccata = models.BooleanField(default=False)
    motivo_blocco = models.TextField(blank=True, null=True)
    libretto_fronte = models.FileField(upload_to=libretto_upload_path, blank=True, null=True)
    libretto_retro = models.FileField(upload_to=libretto_upload_path, blank=True, null=True)
    assicurazione = models.FileField(upload_to=assicurazione_upload_path, blank=True, null=True)
    data_revisione = models.DateField(blank=True, null=True)
    data_scadenza_assicurazione = models.DateField(blank=True, null=True)
    assegnato_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="automezzi_assegnati",
    )

    class Meta:
        verbose_name = "Automezzo"
        verbose_name_plural = "Automezzi"
        ordering = ["targa"]

    def __str__(self):
        return f"{self.targa} - {self.marca} {self.modello}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("automezzi:automezzo_detail", kwargs={"pk": self.pk})

    @classmethod
    def search(cls, query):
        from django.db.models import Q
        q = Q(targa__icontains=query) | Q(marca__icontains=query) | Q(modello__icontains=query)
        return cls.objects.filter(q)[:5]

    def get_search_result_display(self):
        mezzo = f"M{self.numero_mezzo}" if self.numero_mezzo else self.targa
        return f"{mezzo} — {self.marca} {self.modello} ({self.targa})"

    @property
    def eta(self):
        from datetime import date
        return date.today().year - self.anno_immatricolazione


class Manutenzione(AllegatiMixin, models.Model):
    STATO_CHOICES = [
        ("aperta", "Manutenzione Aperta"),
        ("in_corso", "In Corso"),
        ("terminata", "Terminata"),
    ]

    automezzo = models.ForeignKey(Automezzo, on_delete=models.CASCADE, related_name="manutenzioni")
    data_apertura = models.DateTimeField(auto_now_add=True, null=True)
    data_prevista = models.DateField(null=True)
    descrizione = models.CharField(max_length=255)
    stato = models.CharField(max_length=10, choices=STATO_CHOICES, default="aperta")
    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="automezzi_manutenzioni",
    )
    luogo = models.CharField(max_length=200, blank=True)
    costo = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    seguito_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="automezzi_manutenzioni_seguite",
    )
    responsabile = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="automezzi_manutenzioni_responsabile",
    )
    allegati = models.FileField(upload_to=allegati_manutenzione_path, blank=True, null=True)
    data_inizio_manutenzione = models.DateTimeField(null=True, blank=True)
    km_consegna = models.PositiveIntegerField(null=True, blank=True)
    foglio_accettazione = models.FileField(upload_to=allegati_manutenzione_path, blank=True, null=True)
    note_responsabile = models.TextField(blank=True)
    note_finali = models.TextField(blank=True)
    fattura_fornitore = models.FileField(upload_to=allegati_manutenzione_path, blank=True, null=True)
    data_completamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Manutenzione"
        verbose_name_plural = "Manutenzioni"
        ordering = ["-data_prevista"]

    def __str__(self):
        return f"{self.automezzo} - {self.data_prevista} - {self.descrizione}"

    @property
    def is_completata(self):
        return self.stato == "terminata"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("automezzi:manutenzione_detail", kwargs={"pk": self.pk})

    def conta_allegati(self):
        # Override: 'allegati' FileField shadows AllegatiMixin.allegati property
        from core.models_legacy import Allegato
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self.__class__)
        return Allegato.objects.filter(content_type=ct, object_id=self.pk).count()


class AllegatoManutenzione(models.Model):
    manutenzione = models.ForeignKey(Manutenzione, on_delete=models.CASCADE, related_name="allegati_aggiuntivi")
    nome = models.CharField(max_length=200)
    file = models.FileField(upload_to=allegati_manutenzione_path)
    data_upload = models.DateTimeField(auto_now_add=True)
    caricato_da = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Allegato Manutenzione"
        verbose_name_plural = "Allegati Manutenzione"
        ordering = ["-data_upload"]

    def __str__(self):
        return f"{self.manutenzione} - {self.nome}"


class Rifornimento(AllegatiMixin, models.Model):
    automezzo = models.ForeignKey(Automezzo, on_delete=models.CASCADE, related_name="rifornimenti")
    data = models.DateField()
    litri = models.DecimalField(max_digits=6, decimal_places=2)
    costo_totale = models.DecimalField(max_digits=7, decimal_places=2)
    chilometri = models.PositiveIntegerField()
    scontrino = models.FileField(upload_to=scontrino_upload_path, blank=True, null=True)

    class Meta:
        verbose_name = "Rifornimento"
        verbose_name_plural = "Rifornimenti"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.automezzo} - {self.data} - {self.litri}L"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("automezzi:rifornimento_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.chilometri >= self.automezzo.chilometri_attuali:
            Automezzo.objects.filter(pk=self.automezzo_id).update(chilometri_attuali=self.chilometri)


class EventoAutomezzo(AllegatiMixin, models.Model):
    TIPO_EVENTO_CHOICES = [
        ("incidente", "Incidente"),
        ("furto", "Furto"),
        ("fermo", "Fermo amministrativo"),
        ("guasto", "Guasto/avaria"),
        ("altro", "Altro"),
    ]

    automezzo = models.ForeignKey(Automezzo, on_delete=models.CASCADE, related_name="eventi")
    tipo = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    data_evento = models.DateField()
    descrizione = models.TextField(blank=True)
    costo = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dipendente_coinvolto = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="automezzi_eventi_coinvolto",
    )
    file_allegato = models.FileField(upload_to=allegato_evento_path, blank=True, null=True)
    risolto = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Evento Automezzo"
        verbose_name_plural = "Eventi Automezzo"
        ordering = ["-data_evento"]

    def __str__(self):
        return f"{self.automezzo} - {self.get_tipo_display()} - {self.data_evento}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("automezzi:evento_detail", kwargs={"pk": self.pk})
