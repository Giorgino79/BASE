"""
Base Models per ModularBEF

Tutti i models delle app devono ereditare da BaseModel per garantire
consistenza e funzionalità comuni.
"""

from django.db import models
from django.conf import settings
import uuid


class BaseModel(models.Model):
    """
    Abstract base model per tutti i models del progetto.

    Fornisce:
    - UUID come primary key
    - Timestamp di creazione e modifica
    - Tracking utente creatore e modificatore
    - Soft delete capabilities

    Usage:
        class MioModello(BaseModel):
            # i tuoi campi
            nome = models.CharField(max_length=200)
    """

    # UUID Primary Key per maggiore sicurezza e portabilità
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID"
    )

    # Timestamp automatici
    created_at = models.DateTimeField(
        "Data creazione", auto_now_add=True, db_index=True
    )
    updated_at = models.DateTimeField("Data modifica", auto_now=True)

    # Tracking utenti
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name="Creato da",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        verbose_name="Modificato da",
    )

    # Soft delete
    is_active = models.BooleanField("Attivo", default=True, db_index=True)
    deleted_at = models.DateTimeField("Data cancellazione", null=True, blank=True)

    class Meta:
        abstract = True
        get_latest_by = "created_at"
        ordering = ["-created_at"]

    def soft_delete(self, user=None):
        """
        Esegue soft delete del record.

        Args:
            user: Utente che esegue la cancellazione
        """
        from django.utils import timezone

        self.is_active = False
        self.deleted_at = timezone.now()
        if user:
            self.updated_by = user
        self.save()

    def restore(self, user=None):
        """
        Ripristina un record cancellato.

        Args:
            user: Utente che esegue il ripristino
        """
        self.is_active = True
        self.deleted_at = None
        if user:
            self.updated_by = user
        self.save()

    def save(self, *args, **kwargs):
        """Override save per gestire automaticamente created_by/updated_by"""
        # Nota: il tracking dell'utente viene fatto nelle view/form
        # con form.instance.created_by = request.user
        super().save(*args, **kwargs)


class BaseModelWithCode(BaseModel):
    """
    Abstract model con codice univoco automatico.

    Fornisce tutte le funzionalità di BaseModel più:
    - Campo codice univoco
    - Generazione automatica codice se non fornito

    Usage:
        class Ordine(BaseModelWithCode):
            CODE_PREFIX = "ORD"

            # altri campi
            cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    """

    CODE_PREFIX = ""  # Override nelle subclassi (es: "ORD", "FATT")
    CODE_LENGTH = 8  # Lunghezza parte numerica

    codice = models.CharField(
        "Codice", max_length=50, unique=True, db_index=True, editable=False
    )

    class Meta:
        abstract = True

    def generate_code(self):
        """
        Genera codice univoco nel formato: PREFIX-YYYYMMDD-NNNN

        Returns:
            str: Codice generato
        """
        from django.utils import timezone

        today = timezone.now().strftime("%Y%m%d")

        # Trova ultimo codice del giorno
        prefix = f"{self.CODE_PREFIX}-{today}-"
        last_obj = (
            self.__class__.objects.filter(codice__startswith=prefix)
            .order_by("-codice")
            .first()
        )

        if last_obj:
            # Estrai numero e incrementa
            last_number = int(last_obj.codice.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        # Formatta con zero padding
        number_str = str(new_number).zfill(self.CODE_LENGTH)

        return f"{prefix}{number_str}"

    def save(self, *args, **kwargs):
        """Override save per generare codice automaticamente"""
        if not self.codice:
            self.codice = self.generate_code()
        super().save(*args, **kwargs)


class BaseModelSimple(models.Model):
    """
    Versione semplificata di BaseModel senza UUID e soft delete.

    Utile per modelli semplici, lookup tables, o quando serve IntegerField PK.

    Fornisce solo:
    - ID intero auto-increment
    - Timestamp creazione e modifica

    Usage:
        class Categoria(BaseModelSimple):
            nome = models.CharField(max_length=100)
    """

    created_at = models.DateTimeField(
        "Data creazione", auto_now_add=True, db_index=True
    )
    updated_at = models.DateTimeField("Data modifica", auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = "created_at"
        ordering = ["-created_at"]
