from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from core.mixins.model_mixins import AllegatiMixin


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
        related_name="stabilimenti_stabilimenti_operativi",
    )
    responsabile_amministrativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stabilimenti_stabilimenti_amministrativi",
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stabilimenti_stabilimenti_creati",
    )
    modificato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stabilimenti_stabilimenti_modificati",
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
        return reverse("stabilimenti:stabilimento_detail", kwargs={"pk": self.pk})

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
        related_name="stabilimenti_costi_gestiti",
    )
    fornitore = models.ForeignKey(
        "anagrafica.Fornitore",
        on_delete=models.PROTECT,
        related_name="stabilimenti_costi_stabilimenti",
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
    fattura = models.FileField(upload_to="stabilimenti/fatture/%Y/%m/", blank=True, null=True)
    preventivo = models.FileField(upload_to="stabilimenti/preventivi/%Y/%m/", blank=True, null=True)
    certificato = models.FileField(upload_to="stabilimenti/certificati/%Y/%m/", blank=True, null=True)
    allegato1 = models.FileField(upload_to="stabilimenti/allegati/%Y/%m/", blank=True, null=True)
    allegato2 = models.FileField(upload_to="stabilimenti/allegati/%Y/%m/", blank=True, null=True)
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
        return reverse("stabilimenti:costo_detail", kwargs={"pk": self.pk})

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
        related_name="stabilimenti_documenti_caricati",
    )
    nome_documento = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=30, choices=TipoDocumento.choices, default=TipoDocumento.ALTRO)
    versione = models.CharField(max_length=10, default="1.0")
    descrizione = models.TextField(blank=True, null=True)
    file_documento = models.FileField(upload_to="stabilimenti/documenti/%Y/%m/")
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
