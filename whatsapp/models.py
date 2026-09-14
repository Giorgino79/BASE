from django.db import models
from core.models import BaseModel


class WAConfig(BaseModel):
    """Configurazione singleton del modulo WhatsApp."""

    numero_mittente = models.CharField(
        max_length=20, blank=True,
        help_text="Numero WhatsApp del mittente (es: 393331234567)"
    )
    foto_profilo = models.ImageField(
        upload_to="whatsapp/profilo/", blank=True, null=True,
        help_text="Foto profilo da impostare su WhatsApp"
    )
    stato_wa = models.CharField(
        max_length=139, blank=True,
        verbose_name="Stato / About",
        help_text="Testo 'Informazioni' del profilo WhatsApp (max 139 caratteri)"
    )
    delay_min = models.PositiveIntegerField(
        default=8,
        verbose_name="Delay minimo (sec)",
        help_text="Attesa minima tra un messaggio e il successivo"
    )
    delay_max = models.PositiveIntegerField(
        default=20,
        verbose_name="Delay massimo (sec)",
        help_text="Attesa massima tra un messaggio e il successivo"
    )
    attivo = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configurazione WhatsApp"
        verbose_name_plural = "Configurazione WhatsApp"

    def __str__(self):
        return f"Config WA — {self.numero_mittente or 'non configurato'}"

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(
            pk=cls.objects.order_by('created_at').values_list('pk', flat=True).first()
            or "00000000-0000-0000-0000-000000000001"
        )
        return obj

    @classmethod
    def get_or_create_singleton(cls):
        qs = cls.objects.all()
        if qs.exists():
            return qs.first()
        return cls.objects.create()


class WAMessaggio(BaseModel):
    """Log di ogni messaggio WhatsApp inviato."""

    STATO_CHOICES = [
        ("pending", "In attesa"),
        ("sent", "Inviato"),
        ("failed", "Fallito"),
    ]
    TIPO_CHOICES = [
        ("cliente", "Cliente"),
        ("fornitore", "Fornitore"),
        ("manuale", "Manuale"),
        ("broadcast", "Broadcast"),
    ]

    destinatario_numero = models.CharField(max_length=20)
    destinatario_nome = models.CharField(max_length=200, blank=True)
    testo = models.TextField()
    stato = models.CharField(max_length=10, choices=STATO_CHOICES, default="pending")
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default="manuale")
    errore = models.TextField(blank=True)
    inviato_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Messaggio WhatsApp"
        verbose_name_plural = "Messaggi WhatsApp"
        ordering = ["-created_at"]

    def __str__(self):
        return f"→ {self.destinatario_nome or self.destinatario_numero} [{self.get_stato_display()}]"


class WABroadcast(BaseModel):
    """Campagna di invio multiplo a una lista di contatti."""

    STATO_CHOICES = [
        ("bozza", "Bozza"),
        ("in_corso", "In corso"),
        ("completata", "Completata"),
        ("annullata", "Annullata"),
    ]

    titolo = models.CharField(max_length=200)
    messaggio = models.TextField()
    stato = models.CharField(max_length=12, choices=STATO_CHOICES, default="bozza")
    avviato_at = models.DateTimeField(null=True, blank=True)
    completato_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Broadcast WhatsApp"
        verbose_name_plural = "Broadcast WhatsApp"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titolo} [{self.get_stato_display()}]"

    @property
    def totale(self):
        return self.destinatari.count()

    @property
    def inviati(self):
        return self.destinatari.filter(stato="sent").count()

    @property
    def falliti(self):
        return self.destinatari.filter(stato="failed").count()

    @property
    def in_attesa(self):
        return self.destinatari.filter(stato="pending").count()


class WABroadcastDestinatario(BaseModel):
    """Singolo destinatario di un broadcast."""

    STATO_CHOICES = [
        ("pending", "In attesa"),
        ("sent", "Inviato"),
        ("failed", "Fallito"),
        ("skipped", "Saltato"),
    ]

    broadcast = models.ForeignKey(
        WABroadcast, on_delete=models.CASCADE, related_name="destinatari"
    )
    numero = models.CharField(max_length=20)
    nome = models.CharField(max_length=200, blank=True)
    stato = models.CharField(max_length=10, choices=STATO_CHOICES, default="pending")
    errore = models.CharField(max_length=500, blank=True)
    inviato_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Destinatario broadcast"
        verbose_name_plural = "Destinatari broadcast"

    def __str__(self):
        return f"{self.nome or self.numero} [{self.get_stato_display()}]"
