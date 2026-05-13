from django.conf import settings
from django.db import models
from django.db.models import Max
from django.utils import timezone


class TipoCorrispondenza(models.Model):
    nome = models.CharField(max_length=50, verbose_name='Nome')
    descrizione = models.TextField(blank=True, verbose_name='Descrizione')
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo Corrispondenza'
        verbose_name_plural = 'Tipi Corrispondenza'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Corrispondenza(models.Model):

    class TipoDestinatario(models.TextChoices):
        INTERNO = 'interno', 'Utente interno'
        ESTERNO = 'esterno', 'Destinatario esterno'

    class Stato(models.TextChoices):
        BOZZA = 'bozza', 'Bozza'
        INVIATA = 'inviata', 'Inviata'
        ARCHIVIATA = 'archiviata', 'Archiviata'

    class Priorita(models.TextChoices):
        BASSA = 'bassa', 'Bassa'
        NORMALE = 'normale', 'Normale'
        ALTA = 'alta', 'Alta'
        URGENTE = 'urgente', 'Urgente'

    numero_protocollo = models.CharField(
        max_length=20, unique=True, blank=True,
        verbose_name='N. Protocollo',
        help_text='Generato automaticamente: CORyyyyNNNN'
    )
    oggetto = models.CharField(max_length=200, verbose_name='Oggetto')
    contenuto = models.TextField(verbose_name='Contenuto')
    data_invio = models.DateField(null=True, blank=True, verbose_name='Data Invio')

    stato = models.CharField(
        max_length=20, choices=Stato.choices, default=Stato.BOZZA,
        verbose_name='Stato'
    )
    priorita = models.CharField(
        max_length=10, choices=Priorita.choices, default=Priorita.NORMALE,
        verbose_name='Priorità'
    )
    tipo_destinatario = models.CharField(
        max_length=20, choices=TipoDestinatario.choices, default=TipoDestinatario.ESTERNO,
        verbose_name='Tipo Destinatario'
    )

    # Destinatario interno (utente del sistema)
    destinatario_utente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='corrispondenze_ricevute',
        verbose_name='Destinatario (utente)'
    )

    # Destinatario esterno (manuale)
    destinatario_nome = models.CharField(max_length=200, blank=True, verbose_name='Nome / Ragione Sociale')
    destinatario_indirizzo = models.CharField(max_length=200, blank=True, verbose_name='Indirizzo')
    destinatario_cap = models.CharField(max_length=10, blank=True, verbose_name='CAP')
    destinatario_citta = models.CharField(max_length=100, blank=True, verbose_name='Città')
    destinatario_provincia = models.CharField(max_length=5, blank=True, verbose_name='Prov.')
    destinatario_email = models.EmailField(blank=True, verbose_name='Email Destinatario')
    destinatario_telefono = models.CharField(max_length=20, blank=True, verbose_name='Tel.')

    tipo_corrispondenza = models.ForeignKey(
        TipoCorrispondenza,
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Tipo'
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='corrispondenze_create',
        verbose_name='Creato da'
    )
    note_interne = models.TextField(blank=True, verbose_name='Note Interne')
    allegato = models.FileField(
        upload_to='corrispondenza/allegati/%Y/%m/',
        null=True, blank=True,
        verbose_name='Allegato'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Corrispondenza'
        verbose_name_plural = 'Corrispondenze'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all', 'Può visualizzare tutta la corrispondenza'),
            ('can_send', 'Può inviare corrispondenza'),
        ]

    def __str__(self):
        return f"{self.numero_protocollo} — {self.oggetto[:50]}"

    def save(self, *args, **kwargs):
        if not self.numero_protocollo:
            self.numero_protocollo = self._genera_numero_protocollo()
        super().save(*args, **kwargs)

    def _genera_numero_protocollo(self):
        anno = timezone.now().year
        prefisso = f'COR{anno}'
        ultimo = Corrispondenza.objects.filter(
            numero_protocollo__startswith=prefisso
        ).aggregate(m=Max('numero_protocollo'))['m']
        if ultimo:
            try:
                n = int(ultimo[len(prefisso):])
            except (ValueError, IndexError):
                n = 0
        else:
            n = 0
        return f'{prefisso}{(n + 1):04d}'

    def get_destinatario_display(self):
        if self.tipo_destinatario == self.TipoDestinatario.INTERNO and self.destinatario_utente:
            return self.destinatario_utente.get_full_name() or self.destinatario_utente.username
        return self.destinatario_nome or '—'

    def get_destinatario_email(self):
        if self.tipo_destinatario == self.TipoDestinatario.INTERNO and self.destinatario_utente:
            return self.destinatario_utente.email
        return self.destinatario_email

    @property
    def can_edit(self):
        return self.stato == self.Stato.BOZZA

    @property
    def stato_color(self):
        return {'bozza': '#f59e0b', 'inviata': '#22c55e', 'archiviata': '#94a3b8'}.get(self.stato, '#94a3b8')

    @property
    def priorita_color(self):
        return {'bassa': '#22c55e', 'normale': '#6366f1', 'alta': '#f59e0b', 'urgente': '#ef4444'}.get(self.priorita, '#6366f1')
