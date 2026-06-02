from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from datetime import date
from core.mixins.model_mixins import AllegatiMixin


# ============================================================
# UPLOAD PATHS
# ============================================================

def libretto_upload_path(instance, filename):
    return f"cespiti/automezzi/libretti/{instance.targa}/{filename}"


def assicurazione_upload_path(instance, filename):
    return f"cespiti/automezzi/assicurazioni/{instance.targa}/{filename}"


def scontrino_upload_path(instance, filename):
    return f"cespiti/rifornimenti/{instance.automezzo.targa}/{filename}"


def allegati_manutenzione_path(instance, filename):
    return f"cespiti/manutenzioni/{filename}"


def allegato_evento_path(instance, filename):
    return f"cespiti/eventi/{filename}"


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
        related_name="cespiti_automezzi_assegnati",
    )

    class Meta:
        verbose_name = "Automezzo"
        verbose_name_plural = "Automezzi"
        ordering = ["targa"]

    def __str__(self):
        return f"{self.targa} - {self.marca} {self.modello}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("cespiti:automezzo_detail", kwargs={"pk": self.pk})

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
        related_name="cespiti_manutenzioni",
    )
    luogo = models.CharField(max_length=200, blank=True)
    costo = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    seguito_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cespiti_manutenzioni_seguite",
    )
    responsabile = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cespiti_manutenzioni_responsabile",
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
        return reverse("cespiti:manutenzione_detail", kwargs={"pk": self.pk})

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
        return reverse("cespiti:rifornimento_detail", kwargs={"pk": self.pk})

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
        related_name="cespiti_eventi_coinvolto",
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
        return reverse("cespiti:evento_detail", kwargs={"pk": self.pk})


# ============================================================
# STABILIMENTI
# ============================================================

class StabilimentoManager(models.Manager):
    def attivi(self):
        return self.filter(attivo=True)

    def con_scadenze_prossime(self, giorni=30):
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.filter(
            costi__data_scadenza_servizio__lte=data_limite,
            costi__data_scadenza_servizio__gte=timezone.now().date(),
        ).distinct()


class Stabilimento(AllegatiMixin, models.Model):
    nome = models.CharField(max_length=200)
    codice_stabilimento = models.CharField(max_length=10, unique=True)
    indirizzo = models.CharField(max_length=300)
    cap = models.CharField(
        max_length=5,
        validators=[RegexValidator(regex=r"^\d{5}$", message="Il CAP deve essere di 5 cifre")],
    )
    citta = models.CharField(max_length=100)
    provincia = models.CharField(
        max_length=2,
        validators=[RegexValidator(regex=r"^[A-Z]{2}$", message="Provincia: 2 lettere maiuscole")],
    )
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email_filiale = models.EmailField(blank=True, null=True)
    responsabile_operativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cespiti_stabilimenti_operativi",
    )
    responsabile_amministrativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cespiti_stabilimenti_amministrativi",
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cespiti_stabilimenti_creati",
    )
    modificato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cespiti_stabilimenti_modificati",
        null=True, blank=True,
    )
    superficie_mq = models.PositiveIntegerField(blank=True, null=True)
    numero_piani = models.PositiveSmallIntegerField(default=1)
    anno_costruzione = models.PositiveSmallIntegerField(blank=True, null=True)
    attivo = models.BooleanField(default=True)
    data_apertura = models.DateField(blank=True, null=True)
    data_chiusura = models.DateField(blank=True, null=True)
    note_generali = models.TextField(blank=True, null=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    objects = StabilimentoManager()

    class Meta:
        verbose_name = "Stabilimento"
        verbose_name_plural = "Stabilimenti"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codice_stabilimento} - {self.nome}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("cespiti:stabilimento_detail", kwargs={"pk": self.pk})

    @classmethod
    def search(cls, query):
        from django.db.models import Q
        q = Q(nome__icontains=query) | Q(codice_stabilimento__icontains=query) | Q(citta__icontains=query)
        return cls.objects.filter(q)[:5]

    def get_search_result_display(self):
        return f"{self.codice_stabilimento} — {self.nome} ({self.citta})"

    def save(self, *args, **kwargs):
        if not self.codice_stabilimento:
            self.codice_stabilimento = self._genera_codice()
        super().save(*args, **kwargs)

    def _genera_codice(self):
        n = Stabilimento.objects.filter(codice_stabilimento__startswith="STB").count()
        return f"STB{(n + 1):03d}"

    def get_indirizzo_completo(self):
        return f"{self.indirizzo}, {self.cap} {self.citta} ({self.provincia})"

    def get_costi_anno_corrente(self):
        anno = timezone.now().year
        return self.costi.filter(data_creazione__year=anno).aggregate(
            totale=models.Sum("importo")
        )["totale"] or Decimal("0.00")

    def get_prossime_scadenze(self, giorni=30):
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.costi.filter(
            data_scadenza_servizio__lte=data_limite,
            data_scadenza_servizio__gte=timezone.now().date(),
        ).order_by("data_scadenza_servizio")

    def has_scadenze_urgenti(self, giorni=7):
        return self.get_prossime_scadenze(giorni).exists()


class CostiStabilimentoManager(models.Manager):
    def per_tipo(self, tipo_costo):
        return self.filter(causale=tipo_costo)

    def scadenze_prossime(self, giorni=30):
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.filter(
            data_scadenza_servizio__lte=data_limite,
            data_scadenza_servizio__gte=timezone.now().date(),
        )

    def dell_anno(self, anno):
        return self.filter(data_fattura__year=anno)


class CostiStabilimento(AllegatiMixin, models.Model):
    class TipoCosto(models.TextChoices):
        MANUTENZIONE_ORDINARIA = "manutenzione_ordinaria", "Manutenzione Ordinaria"
        MANUTENZIONE_STRAORDINARIA = "manutenzione_straordinaria", "Manutenzione Straordinaria"
        ADEGUAMENTO = "adeguamento", "Adeguamento Strutturale"
        SERVIZI_PERIODICI = "servizi_periodici", "Servizi Periodici"
        CERTIFICAZIONI = "certificazioni", "Certificazioni Obbligatorie"
        ENERGIA_ELETTRICA = "energia_elettrica", "Energia Elettrica"
        GAS_NATURALE = "gas_naturale", "Gas Naturale"
        ACQUA = "acqua", "Acqua e Scarichi"
        TELEFONIA = "telefonia", "Telefonia e Internet"
        RIFIUTI = "rifiuti", "Smaltimento Rifiuti"
        SICUREZZA = "sicurezza", "Sicurezza e Vigilanza"
        PULIZIE = "pulizie", "Servizi di Pulizia"
        ASSICURAZIONI = "assicurazioni", "Assicurazioni"
        TASSE = "tasse", "Tasse e Tributi"
        ALTRO = "altro", "Altro"

    class StatoCosto(models.TextChoices):
        PREVENTIVO = "preventivo", "Preventivo"
        APPROVATO = "approvato", "Approvato"
        IN_CORSO = "in_corso", "In Corso"
        COMPLETATO = "completato", "Completato"
        FATTURATO = "fatturato", "Fatturato"
        PAGATO = "pagato", "Pagato"

    stabilimento = models.ForeignKey(Stabilimento, on_delete=models.PROTECT, related_name="costi")
    incaricato = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cespiti_costi_gestiti",
    )
    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.PROTECT,
        related_name="cespiti_costi_stabilimenti",
    )
    numero_pratica = models.CharField(max_length=50, unique=True)
    causale = models.CharField(
        max_length=50,
        choices=TipoCosto.choices,
        default=TipoCosto.SERVIZI_PERIODICI,
    )
    stato = models.CharField(max_length=20, choices=StatoCosto.choices, default=StatoCosto.PREVENTIVO)
    titolo = models.CharField(max_length=200)
    descrizione = models.TextField()
    importo = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    iva_percentuale = models.DecimalField(
        max_digits=5, decimal_places=2, default=22,
        validators=[MinValueValidator(Decimal("0"))],
    )
    data_richiesta = models.DateField(default=timezone.now)
    data_inizio_lavori = models.DateField(blank=True, null=True)
    data_fine_lavori = models.DateField(blank=True, null=True)
    data_fattura = models.DateField(blank=True, null=True)
    data_scadenza_servizio = models.DateField(blank=True, null=True, verbose_name="Prossima Scadenza")
    fattura = models.FileField(upload_to="cespiti/fatture/%Y/%m/", blank=True, null=True)
    preventivo = models.FileField(upload_to="cespiti/preventivi/%Y/%m/", blank=True, null=True)
    certificato = models.FileField(upload_to="cespiti/certificati/%Y/%m/", blank=True, null=True)
    allegato1 = models.FileField(upload_to="cespiti/allegati/%Y/%m/", blank=True, null=True)
    allegato2 = models.FileField(upload_to="cespiti/allegati/%Y/%m/", blank=True, null=True)
    note_interne = models.TextField(blank=True, null=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    # Campi specifici utenze
    consumo_kwh = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    consumo_mc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    periodo_fatturazione_da = models.DateField(null=True, blank=True)
    periodo_fatturazione_a = models.DateField(null=True, blank=True)
    codice_pdr_pod = models.CharField(max_length=50, null=True, blank=True)

    objects = CostiStabilimentoManager()

    class Meta:
        verbose_name = "Costo Stabilimento"
        verbose_name_plural = "Costi Stabilimenti"
        ordering = ["-data_creazione"]

    def __str__(self):
        return f"{self.numero_pratica} - {self.titolo} ({self.stabilimento.nome})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("cespiti:costo_detail", kwargs={"pk": self.pk})

    @classmethod
    def search(cls, query):
        from django.db.models import Q
        q = (Q(numero_pratica__icontains=query) | Q(titolo__icontains=query)
             | Q(stabilimento__nome__icontains=query))
        return cls.objects.filter(q)[:5]

    def get_search_result_display(self):
        return f"{self.numero_pratica} — {self.titolo} ({self.stabilimento.nome})"

    def save(self, *args, **kwargs):
        if not self.numero_pratica:
            self.numero_pratica = self._genera_numero_pratica()
        super().save(*args, **kwargs)

    def _genera_numero_pratica(self):
        anno = timezone.now().year
        n = CostiStabilimento.objects.filter(numero_pratica__startswith=f"STB-{anno}-").count()
        return f"STB-{anno}-{(n + 1):04d}"

    def calcola_totale_con_iva(self):
        return self.importo * (1 + (self.iva_percentuale / Decimal("100")))

    def calcola_iva(self):
        return self.importo * (self.iva_percentuale / Decimal("100"))

    def is_scaduto(self):
        if self.data_scadenza_servizio:
            return self.data_scadenza_servizio < timezone.now().date()
        return False

    def giorni_alla_scadenza(self):
        if self.data_scadenza_servizio:
            return (self.data_scadenza_servizio - timezone.now().date()).days
        return None

    def is_in_scadenza(self, giorni=30):
        g = self.giorni_alla_scadenza()
        return g is not None and 0 <= g <= giorni

    def can_be_deleted(self):
        return self.stato in [self.StatoCosto.PREVENTIVO, self.StatoCosto.APPROVATO]

    def can_be_modified(self):
        return self.stato != self.StatoCosto.PAGATO


class DocStabilimento(models.Model):
    class TipoDocumento(models.TextChoices):
        SCIA = "scia", "SCIA"
        AUTORIZZAZIONE = "autorizzazione", "Autorizzazione Edilizia"
        PERMESSO_COSTRUIRE = "permesso_costruire", "Permesso di Costruire"
        CONTRATTO_DERATTIZZAZIONE = "contratto_derattizzazione", "Contratto Derattizzazione"
        CONTRATTO_DISINFESTAZIONE = "contratto_disinfestazione", "Contratto Disinfestazione"
        CONTRATTO_PULIZIE = "contratto_pulizie", "Contratto Pulizie"
        CONTRATTO_VIGILANZA = "contratto_vigilanza", "Contratto Vigilanza"
        CONTRATTO_MANUTENZIONE = "contratto_manutenzione", "Contratto Manutenzione"
        CERTIFICATO_PREVENZIONE_INCENDI = "cert_prevenzione_incendi", "Certificato Prevenzione Incendi"
        CERTIFICATO_AGIBILITA = "cert_agibilita", "Certificato di Agibilità"
        CERTIFICATO_CONFORMITA = "cert_conformita", "Certificato di Conformità"
        COLLAUDO_IMPIANTI = "collaudo_impianti", "Collaudo Impianti"
        VERIFICA_ASCENSORI = "verifica_ascensori", "Verifica Ascensori"
        CONTROLLO_CALDAIE = "controllo_caldaie", "Controllo Caldaie"
        CONTROLLO_ANTINCENDIO = "controllo_antincendio", "Controllo Antincendio"
        PLANIMETRIA = "planimetria", "Planimetria"
        VERBALE = "verbale", "Verbale Controllo"
        CONTRATTO = "contratto", "Contratto Generico"
        CERTIFICAZIONE = "certificazione", "Certificazione Generica"
        ALTRO = "altro", "Altro"

    stabilimento = models.ForeignKey(Stabilimento, on_delete=models.PROTECT, related_name="documenti")
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cespiti_documenti_caricati",
    )
    nome_documento = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=30, choices=TipoDocumento.choices, default=TipoDocumento.ALTRO)
    versione = models.CharField(max_length=10, default="1.0")
    descrizione = models.TextField(blank=True, null=True)
    file_documento = models.FileField(upload_to="cespiti/documenti/%Y/%m/")
    data_documento = models.DateField(blank=True, null=True)
    data_scadenza = models.DateField(blank=True, null=True)
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)
    data_inserimento = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento Stabilimento"
        verbose_name_plural = "Documenti Stabilimenti"
        ordering = ["-data_inserimento"]

    def __str__(self):
        return f"{self.nome_documento} v{self.versione} - {self.stabilimento.nome}"

    def is_scaduto(self):
        if self.data_scadenza:
            return self.data_scadenza < timezone.now().date()
        return False

    def giorni_alla_scadenza(self):
        if self.data_scadenza:
            return (self.data_scadenza - timezone.now().date()).days
        return None
