from django.db import models
from django.conf import settings


class InvioLog(models.Model):
    CANALE_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("entrambi", "WhatsApp + Email"),
    ]
    STATO_CHOICES = [
        ("pending", "In attesa"),
        ("inviato", "Inviato"),
        ("errore", "Errore"),
    ]

    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="invii_log", verbose_name="Inviato da",
    )
    canale = models.CharField("Canale", max_length=10, choices=CANALE_CHOICES)
    destinatario_nome = models.CharField("Nome destinatario", max_length=200, blank=True)
    telefono = models.CharField("Telefono WA", max_length=25, blank=True)
    email = models.EmailField("Email", blank=True)
    oggetto = models.CharField("Oggetto / titolo", max_length=255, blank=True)
    messaggio = models.TextField("Messaggio", blank=True)
    ha_pdf = models.BooleanField("Con PDF allegato", default=False)
    stato = models.CharField("Stato", max_length=10, choices=STATO_CHOICES, default="pending")
    errore_dettaglio = models.TextField("Dettaglio errore", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_invia_log"
        verbose_name = "Log invio"
        verbose_name_plural = "Log invii"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stato", "canale"]),
            models.Index(fields=["utente", "created_at"]),
        ]

    def __str__(self):
        dest = self.destinatario_nome or self.telefono or self.email or "—"
        return f"[{self.get_canale_display()}] {dest} — {self.created_at:%d/%m/%Y %H:%M}"
