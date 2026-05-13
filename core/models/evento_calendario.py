"""
Modello EventoCalendario — eventi manuali creati dagli utenti.

Supporta eventi personali (visibili solo al creatore) e
aziendali (visibili a tutti gli utenti autenticati).
"""

from django.db import models
from django.conf import settings


class EventoCalendario(models.Model):
    """
    Evento manuale del calendario, creato da un utente.

    Visibilità:
    - 'personale': visibile solo al creatore
    - 'aziendale': visibile a tutti gli utenti autenticati
    """

    VISIBILITA_CHOICES = [
        ('personale', 'Solo io'),
        ('aziendale', 'Tutti (aziendale)'),
    ]

    COLORE_CHOICES = [
        ('#007bff', 'Blu'),
        ('#28a745', 'Verde'),
        ('#dc3545', 'Rosso'),
        ('#ffc107', 'Giallo'),
        ('#17a2b8', 'Ciano'),
        ('#fd7e14', 'Arancione'),
        ('#6f42c1', 'Viola'),
        ('#6c757d', 'Grigio'),
    ]

    titolo = models.CharField('Titolo', max_length=200)
    descrizione = models.TextField('Descrizione', blank=True)

    data_inizio = models.DateTimeField('Data/ora inizio')
    data_fine = models.DateTimeField('Data/ora fine', null=True, blank=True)
    tutto_il_giorno = models.BooleanField('Tutto il giorno', default=False)

    colore = models.CharField(
        'Colore',
        max_length=7,
        choices=COLORE_CHOICES,
        default='#007bff',
    )
    visibilita = models.CharField(
        'Visibilità',
        max_length=20,
        choices=VISIBILITA_CHOICES,
        default='personale',
    )

    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='eventi_calendario',
        verbose_name='Creato da',
    )

    created_at = models.DateTimeField('Creato il', auto_now_add=True)
    updated_at = models.DateTimeField('Modificato il', auto_now=True)

    class Meta:
        verbose_name = 'Evento Calendario'
        verbose_name_plural = 'Eventi Calendario'
        ordering = ['data_inizio']
        indexes = [
            models.Index(fields=['data_inizio', 'data_fine']),
            models.Index(fields=['creato_da', 'visibilita']),
        ]

    def __str__(self):
        return f'{self.titolo} ({self.data_inizio.strftime("%d/%m/%Y")})'

    def to_fullcalendar(self, include_url=True):
        """Restituisce il dict in formato FullCalendar."""
        from django.urls import reverse
        event = {
            'id': f'evento-{self.pk}',
            'title': self.titolo,
            'start': self.data_inizio.isoformat(),
            'color': self.colore,
            'allDay': self.tutto_il_giorno,
            'extendedProps': {
                'tipo': 'evento_manuale',
                'visibilita': self.get_visibilita_display(),
                'descrizione': self.descrizione[:100] if self.descrizione else '',
                'creato_da': self.creato_da.get_full_name() or self.creato_da.username,
            }
        }
        if self.data_fine:
            event['end'] = self.data_fine.isoformat()
        if include_url:
            event['url'] = reverse('core:evento_calendario_update', kwargs={'pk': self.pk})
        return event
