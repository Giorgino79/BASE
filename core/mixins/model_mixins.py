"""
Model Mixins per ModularBEF

Mixins riutilizzabili da applicare ai models per aggiungere funzionalità comuni.
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.urls import reverse


# ============================================================================
# TIMESTAMP & TRACKING
# ============================================================================


class TimestampMixin(models.Model):
    """
    Mixin per tracciare data creazione e modifica.

    NOTA: Già incluso in BaseModel, usa questo solo se non erediti da BaseModel.
    """

    created_at = models.DateTimeField("Data creazione", auto_now_add=True)
    updated_at = models.DateTimeField("Data modifica", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Mixin per soft delete (cancellazione logica).

    NOTA: Già incluso in BaseModel, usa questo solo se non erediti da BaseModel.
    """

    deleted_at = models.DateTimeField("Data cancellazione", null=True, blank=True)
    is_active = models.BooleanField("Attivo", default=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """Esegue soft delete"""
        from django.utils import timezone

        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def restore(self, user=None):
        """Ripristina record cancellato"""
        self.is_active = True
        self.deleted_at = None
        self.save()


# ============================================================================
# ALLEGATI
# ============================================================================


class AllegatiMixin(models.Model):
    """
    Mixin per aggiungere gestione allegati a qualsiasi model.

    Usage:
        class MioModello(BaseModel, AllegatiMixin):
            pass

        # Nel codice:
        obj.allegati  # QuerySet di allegati
        obj.aggiungi_allegato(file, descrizione, user)
        obj.get_allegati_pdf()
        obj.conta_allegati()
    """

    class Meta:
        abstract = True

    @property
    def allegati(self):
        """Restituisce tutti gli allegati collegati a questo oggetto"""
        from core.models_legacy import Allegato

        content_type = ContentType.objects.get_for_model(self.__class__)
        return Allegato.objects.filter(content_type=content_type, object_id=self.pk)

    def aggiungi_allegato(self, file, descrizione="", user=None):
        """
        Aggiunge un allegato a questo oggetto.

        Args:
            file: File da allegare
            descrizione: Descrizione opzionale
            user: Utente che carica il file

        Returns:
            Allegato: Oggetto allegato creato
        """
        from core.models_legacy import Allegato

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


# ============================================================================
# QR CODE
# ============================================================================


class QRCodeMixin(models.Model):
    """
    Mixin per generazione QR Code che punta all'oggetto.

    Usage:
        class MioModello(BaseModel, QRCodeMixin):
            def get_absolute_url(self):
                return reverse('app:model_detail', kwargs={'pk': self.pk})

        # Nel codice:
        obj.get_qr_code_url()  # URL per scaricare QR
        obj.generate_qr_code()  # Genera QR code SVG/PNG
        obj.get_qr_code_data() # Ottiene URL dell'oggetto

        # Nel template:
        {% load qr_code %}
        {% qr_code_for object %}
    """

    class Meta:
        abstract = True

    def get_qr_code_data(self):
        """
        Restituisce l'URL completo dell'oggetto per il QR code.

        Returns:
            str: URL completo dell'oggetto
        """
        from django.contrib.sites.shortcuts import get_current_site
        from django.conf import settings

        if hasattr(self, "get_absolute_url"):
            relative_url = self.get_absolute_url()
            # In produzione usa il dominio corretto
            domain = getattr(settings, "SITE_DOMAIN", "localhost:8000")
            protocol = "https" if not settings.DEBUG else "http"
            return f"{protocol}://{domain}{relative_url}"
        return ""

    def get_qr_code_url(self):
        """
        Restituisce l'URL per scaricare il QR code.

        Returns:
            str: URL endpoint per generare QR code
        """
        app_label = self._meta.app_label
        model_name = self._meta.model_name
        return reverse(
            f"{app_label}:{model_name}_qrcode",
            kwargs={"pk": self.pk},
        )

    def generate_qr_code(self, format="svg"):
        """
        Genera il QR code dell'oggetto.

        Args:
            format: Formato output ('svg' o 'png')

        Returns:
            str or bytes: QR code generato
        """
        import qrcode
        import qrcode.image.svg
        from io import BytesIO

        data = self.get_qr_code_data()

        if format == "svg":
            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(data, image_factory=factory)
            buffer = BytesIO()
            img.save(buffer)
            return buffer.getvalue().decode("utf-8")
        else:
            img = qrcode.make(data)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()


# ============================================================================
# PDF EXPORT
# ============================================================================


class PDFMixin(models.Model):
    """
    Mixin per generazione PDF da template HTML.

    Usage:
        class MioModello(BaseModel, PDFMixin):
            def get_pdf_template_name(self):
                return 'app/pdf/model_pdf.html'

            def get_pdf_context(self):
                return {'object': self, 'extra_data': 'value'}

            def get_pdf_filename(self):
                return f"documento_{self.pk}.pdf"

        # Nel codice:
        response = obj.generate_pdf()  # HttpResponse con PDF
        pdf_bytes = obj.generate_pdf_bytes()  # Bytes del PDF
    """

    class Meta:
        abstract = True

    def get_pdf_template_name(self):
        """
        Restituisce il nome del template per il PDF.

        Override questo metodo nelle subclassi.

        Returns:
            str: Path template (es: 'vendite/pdf/ordine_pdf.html')
        """
        app_label = self._meta.app_label
        model_name = self._meta.model_name
        return f"{app_label}/pdf/{model_name}_pdf.html"

    def get_pdf_context(self):
        """
        Restituisce il context dictionary per il template PDF.

        Override questo metodo per aggiungere dati al context.

        Returns:
            dict: Context per template
        """
        return {"object": self}

    def get_pdf_filename(self):
        """
        Restituisce il nome file per il PDF.

        Override questo metodo per customizzare il nome.

        Returns:
            str: Nome file PDF
        """
        model_name = self._meta.model_name
        return f"{model_name}_{self.pk}.pdf"

    def generate_pdf_bytes(self):
        """
        Genera il PDF e restituisce i bytes.

        Returns:
            bytes: Contenuto PDF
        """
        from xhtml2pdf import pisa
        from django.template.loader import render_to_string
        from io import BytesIO

        template_name = self.get_pdf_template_name()
        context = self.get_pdf_context()

        html_string = render_to_string(template_name, context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)

        if pdf.err:
            raise Exception(f"Errore generazione PDF: {pdf.err}")

        return result.getvalue()

    def generate_pdf(self):
        """
        Genera il PDF e restituisce HttpResponse.

        Returns:
            HttpResponse: Response con PDF
        """
        from django.http import HttpResponse

        pdf_bytes = self.generate_pdf_bytes()
        filename = self.get_pdf_filename()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


# ============================================================================
# AUDIT LOG
# ============================================================================


class AuditMixin(models.Model):
    """
    Mixin per tracking dettagliato delle modifiche.

    Salva uno storico di tutte le modifiche al model.

    Usage:
        class MioModello(BaseModel, AuditMixin):
            pass

        # Nel codice:
        obj.get_history()  # Ottiene storico modifiche
        obj.log_change(user, action, details)  # Log manuale
    """

    class Meta:
        abstract = True

    def get_history(self):
        """
        Restituisce lo storico delle modifiche.

        Returns:
            QuerySet: AuditLog entries
        """
        from core.models_legacy import AuditLog

        content_type = ContentType.objects.get_for_model(self.__class__)
        return AuditLog.objects.filter(
            content_type=content_type, object_id=self.pk
        ).order_by("-created_at")

    def log_change(self, user, action, details=None):
        """
        Registra una modifica nell'audit log.

        Args:
            user: Utente che ha fatto la modifica
            action: Tipo azione (CREATE, UPDATE, DELETE, etc)
            details: Dettagli opzionali (dict)
        """
        from core.models_legacy import AuditLog

        content_type = ContentType.objects.get_for_model(self.__class__)
        AuditLog.objects.create(
            content_type=content_type,
            object_id=self.pk,
            user=user,
            action=action,
            details=details or {},
        )

    def save(self, *args, **kwargs):
        """Override save per logging automatico"""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Log automatico (opzionale, può essere pesante)
        # if hasattr(self, '_current_user'):
        #     action = 'CREATE' if is_new else 'UPDATE'
        #     self.log_change(self._current_user, action)
