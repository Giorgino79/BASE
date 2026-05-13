from django.db import models
from django.conf import settings


class Promemoria(models.Model):
    PRIORITA_CHOICES = [
        ('bassa', 'Bassa'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    STATO_CHOICES = [
        ('pending', 'In attesa'),
        ('in_corso', 'In corso'),
        ('completato', 'Completato'),
        ('annullato', 'Annullato'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='promemoria', verbose_name='Creato da',
    )
    assegnato_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='promemoria_assegnati', verbose_name='Assegnato a',
    )
    titolo = models.CharField('Titolo', max_length=200)
    descrizione = models.TextField('Descrizione', blank=True)
    priorita = models.CharField('Priorità', max_length=10, choices=PRIORITA_CHOICES, default='media')
    stato = models.CharField('Stato', max_length=15, choices=STATO_CHOICES, default='pending')
    data_scadenza = models.DateTimeField('Data scadenza', null=True, blank=True)
    completato_il = models.DateTimeField('Completato il', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comunicazioni_promemoria'
        verbose_name = 'Promemoria'
        verbose_name_plural = 'Promemoria'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'stato']),
            models.Index(fields=['data_scadenza']),
        ]

    def __str__(self):
        return self.titolo

    @property
    def is_scaduto(self):
        from django.utils import timezone
        return (self.data_scadenza and self.data_scadenza < timezone.now()
                and self.stato not in ('completato', 'annullato'))

    @property
    def is_attivo(self):
        return self.stato not in ('completato', 'annullato')


class ChatConversazione(models.Model):
    TIPO_CHOICES = [
        ('direct', 'Diretta'),
        ('group', 'Gruppo'),
    ]

    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES, default='direct')
    titolo = models.CharField('Titolo', max_length=200, blank=True)
    partecipanti = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_conversazioni', verbose_name='Partecipanti',
    )
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='chat_conversazioni_create', verbose_name='Creata da',
    )
    last_message_at = models.DateTimeField('Ultimo messaggio', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comunicazioni_chat_conversazione'
        verbose_name = 'Conversazione'
        verbose_name_plural = 'Conversazioni'
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        if self.titolo:
            return self.titolo
        parts = list(self.partecipanti.values_list('first_name', flat=True)[:3])
        return ', '.join(p for p in parts if p) or f'Conversazione #{self.pk}'

    def get_title_for(self, user):
        if self.titolo:
            return self.titolo
        if self.tipo == 'direct':
            other = self.partecipanti.exclude(pk=user.pk).first()
            return other.get_full_name() or other.username if other else 'Chat'
        return self.__str__()

    def unread_count_for(self, user):
        return self.messaggi.exclude(letto_da=user).exclude(mittente=user).count()


class ChatMessaggio(models.Model):
    conversazione = models.ForeignKey(
        ChatConversazione, on_delete=models.CASCADE, related_name='messaggi',
    )
    mittente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='messaggi_inviati',
    )
    contenuto = models.TextField('Messaggio')
    letto_da = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='messaggi_letti', blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comunicazioni_chat_messaggio'
        verbose_name = 'Messaggio'
        verbose_name_plural = 'Messaggi'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.mittente.username}: {self.contenuto[:50]}'
