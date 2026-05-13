from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import os


# ============================================================================
# MIXINS RIUTILIZZABILI
# ============================================================================


class TimestampMixin(models.Model):
    """Mixin per tracciare data creazione e modifica"""

    created_at = models.DateTimeField("Data creazione", auto_now_add=True)
    updated_at = models.DateTimeField("Data modifica", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Mixin per soft delete (cancellazione logica)"""

    deleted_at = models.DateTimeField("Data cancellazione", null=True, blank=True)
    is_active = models.BooleanField("Attivo", default=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Esegue soft delete"""
        from django.utils import timezone

        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Ripristina record cancellato"""
        self.is_active = True
        self.deleted_at = None
        self.save()


class AllegatiMixin(models.Model):
    """Mixin per aggiungere relazione agli allegati"""

    class Meta:
        abstract = True

    @property
    def allegati(self):
        """Restituisce tutti gli allegati collegati a questo oggetto"""
        content_type = ContentType.objects.get_for_model(self.__class__)
        return Allegato.objects.filter(content_type=content_type, object_id=self.pk)

    def aggiungi_allegato(self, file, descrizione="", user=None):
        """Aggiunge un allegato a questo oggetto"""
        content_type = ContentType.objects.get_for_model(self.__class__)
        return Allegato.objects.create(
            content_type=content_type,
            object_id=self.pk,
            file=file,
            descrizione=descrizione,
            uploaded_by=user,
        )

    def get_allegati_per_estensione(self, extension):
        """
        Filtra allegati per estensione.
        Args:
            extension: estensione con punto (es. '.pdf', '.jpg')
        """
        return self.allegati.filter(nome_originale__iendswith=extension)

    def get_allegati_pdf(self):
        """Restituisce solo allegati PDF"""
        return self.get_allegati_per_estensione(".pdf")

    def get_allegati_immagini(self):
        """Restituisce solo allegati immagine"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        q_objects = models.Q()
        for ext in image_extensions:
            q_objects |= models.Q(nome_originale__iendswith=ext)
        return self.allegati.filter(q_objects)

    def get_allegati_documenti(self):
        """Restituisce solo documenti (PDF, DOC, DOCX, XLS, XLSX)"""
        doc_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods"]
        q_objects = models.Q()
        for ext in doc_extensions:
            q_objects |= models.Q(nome_originale__iendswith=ext)
        return self.allegati.filter(q_objects)

    def conta_allegati(self):
        """Restituisce il numero totale di allegati"""
        return self.allegati.count()

    def ha_allegati(self):
        """Verifica se l'oggetto ha almeno un allegato"""
        return self.allegati.exists()

    def genera_e_salva_qr_code(self, data=None, filename="qrcode.png", descrizione="QR Code generato", user=None):
        """
        Genera un QR code e lo salva come allegato dell'oggetto.
        Se 'data' non è fornito, usa l'URL assoluto dell'oggetto.
        """
        from .qr_code_generator import generate_qr_code
        from django.core.files.base import ContentFile

        if not data:
            try:
                data = self.get_absolute_url()
            except (AttributeError, NotImplementedError):
                raise ValueError("Dati per QR code non forniti e get_absolute_url() non implementato")

        qr_buffer = generate_qr_code(data)
        qr_file = ContentFile(qr_buffer.getvalue(), name=filename)

        return self.aggiungi_allegato(
            file=qr_file,
            descrizione=descrizione,
            user=user
        )


class SearchMixin(models.Model):
    """
    Mixin per rendere un model ricercabile nel sistema di ricerca globale.

    Uso:
        class Cliente(SearchMixin, AllegatiMixin, TimestampMixin):
            ragione_sociale = models.CharField(max_length=200)

            @classmethod
            def get_search_fields(cls):
                return ['ragione_sociale', 'partita_iva', 'citta']

            def get_search_result_display(self):
                return f"{self.ragione_sociale} - {self.citta}"
    """

    class Meta:
        abstract = True

    @classmethod
    def get_search_fields(cls):
        """
        Override questo metodo per definire i campi ricercabili.

        Returns:
            list: Lista dei nomi dei campi da ricercare

        Example:
            return ['nome', 'cognome', 'email', 'telefono']
        """
        raise NotImplementedError(
            f"{cls.__name__} deve implementare il metodo get_search_fields()"
        )

    @classmethod
    def search(cls, query):
        """
        Esegue una ricerca nei campi definiti da get_search_fields().

        Args:
            query: stringa di ricerca

        Returns:
            QuerySet: primi 5 risultati ordinati per rilevanza
        """
        if not query or not query.strip():
            return cls.objects.none()

        search_fields = cls.get_search_fields()
        q_objects = models.Q()

        # Crea Q objects per ogni campo ricercabile
        for field in search_fields:
            q_objects |= models.Q(**{f"{field}__icontains": query})

        # Esegue ricerca e limita risultati
        return cls.objects.filter(q_objects)[:5]

    def get_search_result_display(self):
        """
        Override questo metodo per personalizzare il testo visualizzato
        nei risultati di ricerca.

        Returns:
            str: Testo da mostrare nei risultati

        Example:
            return f"{self.nome} {self.cognome} - {self.azienda}"
        """
        return str(self)

    def get_absolute_url(self):
        """
        Deve essere implementato nei model concreti per la navigazione.

        Example:
            from django.urls import reverse
            return reverse('anagrafica:cliente_detail', args=[self.pk])
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} deve implementare get_absolute_url()"
        )


# ============================================================================
# MODELLO ALLEGATI
# ============================================================================


def allegato_upload_path(instance, filename):
    """
    Genera il percorso di upload per gli allegati.
    Struttura: allegati/{app_label}/{model}/{anno}/{mese}/{filename}
    """
    from datetime import datetime

    now = datetime.now()
    content_type = instance.content_type
    return os.path.join(
        "allegati",
        content_type.app_label,
        content_type.model,
        str(now.year),
        f"{now.month:02d}",
        filename,
    )


class Allegato(TimestampMixin):
    """
    Modello per gestire allegati generici collegabili a qualsiasi modello
    tramite GenericForeignKey
    """

    # GenericForeignKey per collegare l'allegato a qualsiasi modello
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name="Tipo contenuto"
    )
    object_id = models.CharField("ID oggetto", max_length=255)  # Supporta sia int che UUID
    content_object = GenericForeignKey("content_type", "object_id")

    # File e metadati
    file = models.FileField("File", upload_to=allegato_upload_path)
    nome_originale = models.CharField("Nome file originale", max_length=255, blank=True)
    descrizione = models.TextField("Descrizione", blank=True)
    dimensione = models.PositiveIntegerField("Dimensione (bytes)", default=0)
    tipo_file = models.CharField("Tipo MIME", max_length=100, blank=True)

    # Tracciamento
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Caricato da",
    )

    class Meta:
        verbose_name = "Allegato"
        verbose_name_plural = "Allegati"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.nome_originale or self.file.name}"

    def save(self, *args, **kwargs):
        """Override save per popolare campi automatici"""
        if self.file:
            # Salva nome originale
            if not self.nome_originale:
                self.nome_originale = os.path.basename(self.file.name)

            # Salva dimensione file
            if hasattr(self.file, "size"):
                self.dimensione = self.file.size

            # Salva tipo MIME
            if hasattr(self.file, "content_type"):
                self.tipo_file = self.file.content_type

        super().save(*args, **kwargs)

    def get_file_extension(self):
        """Restituisce l'estensione del file"""
        return os.path.splitext(self.nome_originale)[1].lower()

    def is_image(self):
        """Verifica se il file è un'immagine"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        """Verifica se il file è un PDF"""
        return self.get_file_extension() == ".pdf"

    def get_size_display(self):
        """Restituisce la dimensione formattata"""
        size = self.dimensione
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def delete(self, *args, **kwargs):
        """Override delete per eliminare anche il file fisico dal filesystem"""
        # Elimina il file fisico prima di eliminare il record dal database
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)


# ============================================================================
# QR CODE
# ============================================================================


def qrcode_upload_path(instance, filename):
    """
    Genera path per salvare i QR Code
    Formato: qrcodes/{content_type}/{object_id}/{filename}
    """
    content_type = instance.content_type.model
    return f"qrcodes/{content_type}/{instance.object_id}/{filename}"


class QRCode(TimestampMixin):
    """
    Modello per gestire QR Code generici collegabili a qualsiasi modello.
    Genera un QR Code che punta a un URL specifico dell'oggetto.
    """

    # GenericForeignKey per collegare il QR Code a qualsiasi modello
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name="Tipo contenuto"
    )
    object_id = models.CharField("ID oggetto", max_length=255)  # Supporta sia int che UUID
    content_object = GenericForeignKey("content_type", "object_id")

    # QR Code file e metadati
    qr_image = models.ImageField("Immagine QR", upload_to=qrcode_upload_path)
    url = models.URLField("URL del QR Code", max_length=500)
    size = models.PositiveIntegerField("Dimensione (px)", default=300)

    # Tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Creato da",
    )

    class Meta:
        verbose_name = "QR Code"
        verbose_name_plural = "QR Codes"
        ordering = ["-created_at"]
        unique_together = [["content_type", "object_id"]]  # Un solo QR Code per oggetto
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"QR Code per {self.content_object}"

    def delete(self, *args, **kwargs):
        """Override delete per eliminare anche il file immagine dal filesystem"""
        if self.qr_image:
            self.qr_image.delete(save=False)
        super().delete(*args, **kwargs)


# ============================================================================
# REGISTRY PATTERN - Gestione Moduli
# ============================================================================


class ModuloRegistryManager(models.Manager):
    """Manager per gestire i moduli attivi"""

    def attivi(self):
        """Restituisce solo i moduli attivi"""
        return self.filter(attivo=True)

    def inattivi(self):
        """Restituisce solo i moduli inattivi"""
        return self.filter(attivo=False)

    def obbligatori(self):
        """Restituisce moduli obbligatori"""
        return self.filter(obbligatorio=True)

    def disattivabili(self):
        """Restituisce moduli disattivabili (non obbligatori)"""
        return self.filter(obbligatorio=False)

    def per_categoria(self, categoria):
        """Restituisce moduli per categoria (solo attivi)"""
        return self.filter(categoria=categoria, attivo=True)

    def per_categoria_tutti(self, categoria):
        """Restituisce tutti i moduli per categoria (attivi e inattivi)"""
        return self.filter(categoria=categoria)


class ModuloRegistry(TimestampMixin):
    """
    Registry Pattern per gestire i moduli installati e attivi nel sistema.
    Permette di attivare/disattivare moduli dinamicamente.
    """

    CATEGORIA_CHOICES = [
        ("base", "Base (obbligatorio)"),
        ("vendite", "Vendite"),
        ("acquisti", "Acquisti"),
        ("magazzino", "Magazzino"),
        ("produzione", "Produzione"),
        ("amministrazione", "Amministrazione"),
        ("hr", "Risorse Umane"),
        ("crm", "CRM"),
        ("altro", "Altro"),
    ]

    # Identificativi modulo
    nome = models.CharField("Nome modulo", max_length=100, unique=True)
    codice = models.SlugField("Codice", max_length=50, unique=True)
    app_name = models.CharField("Nome app Django", max_length=100)

    # Descrizione
    descrizione = models.TextField("Descrizione")
    categoria = models.CharField(
        "Categoria", max_length=50, choices=CATEGORIA_CHOICES, default="altro"
    )

    # Stato
    attivo = models.BooleanField("Attivo", default=False)
    obbligatorio = models.BooleanField(
        "Obbligatorio", default=False, help_text="Moduli obbligatori non disattivabili"
    )

    # Versione e dipendenze
    versione = models.CharField("Versione", max_length=20, default="1.0.0")
    dipendenze = models.JSONField(
        "Dipendenze",
        default=list,
        blank=True,
        help_text="Lista dei codici moduli richiesti",
    )

    # Metadati
    icona = models.CharField("Icona Bootstrap", max_length=50, blank=True)
    ordine = models.PositiveIntegerField("Ordine visualizzazione", default=0)

    objects = ModuloRegistryManager()

    class Meta:
        verbose_name = "Modulo"
        verbose_name_plural = "Moduli"
        ordering = ["ordine", "nome"]
        indexes = [
            models.Index(fields=["attivo"]),
            models.Index(fields=["categoria", "attivo"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.versione})"

    def clean(self):
        """Validazione custom"""
        from django.core.exceptions import ValidationError

        # Non permettere disattivazione moduli obbligatori
        if self.obbligatorio and not self.attivo:
            raise ValidationError("I moduli obbligatori non possono essere disattivati")

        # Verifica dipendenze
        if self.attivo and self.dipendenze:
            for dep_codice in self.dipendenze:
                if not ModuloRegistry.objects.filter(
                    codice=dep_codice, attivo=True
                ).exists():
                    raise ValidationError(
                        f"Il modulo richiede '{dep_codice}' che non è attivo"
                    )

    def attiva(self):
        """Attiva il modulo"""
        self.clean()
        self.attivo = True
        self.save()

    def disattiva(self):
        """Disattiva il modulo"""
        from django.core.exceptions import ValidationError

        if self.obbligatorio:
            raise ValidationError("Impossibile disattivare un modulo obbligatorio")

        # Verifica che nessun modulo attivo dipenda da questo
        dipendenti = ModuloRegistry.objects.filter(
            dipendenze__contains=[self.codice], attivo=True
        )
        if dipendenti.exists():
            raise ValidationError(
                f"Impossibile disattivare: i seguenti moduli dipendono da questo: "
                f"{', '.join(dipendenti.values_list('nome', flat=True))}"
            )

        self.attivo = False
        self.save()

    @classmethod
    def registra_modulo(cls, nome, codice, app_name, **kwargs):
        """
        Registra un nuovo modulo nel sistema.
        Uso: ModuloRegistry.registra_modulo('Vendite', 'vendite', 'vendite', categoria='vendite')
        """
        modulo, created = cls.objects.get_or_create(
            codice=codice,
            defaults={
                "nome": nome,
                "app_name": app_name,
                **kwargs,
            },
        )
        return modulo

    @classmethod
    def get_moduli_attivi(cls):
        """Restituisce la lista dei moduli attivi"""
        return cls.objects.attivi()

    @classmethod
    def is_modulo_attivo(cls, codice):
        """Verifica se un modulo è attivo"""
        return cls.objects.filter(codice=codice, attivo=True).exists()

####GENERA QR CODE

# Import PermissionTemplate per renderlo disponibile a Django
from .models_permissions import PermissionTemplate 
