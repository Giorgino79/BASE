from django.conf import settings
from django.db import models
from django.utils import timezone


class RichiestaIntervento(models.Model):
    URGENZA_CHOICES = [
        ('normale',  'Normale'),
        ('urgente',  'Urgente'),
        ('emergenza','Emergenza'),
    ]

    cliente      = models.ForeignKey(
        'anagrafica.Azienda', on_delete=models.CASCADE,
        related_name='richieste_intervento',
    )
    filiale      = models.ForeignKey(
        'anagrafica.Filiale', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='richieste_intervento',
        verbose_name='Sede',
    )
    tipo_problema = models.CharField(max_length=200, verbose_name='Tipo problema / infestante')
    urgenza       = models.CharField(max_length=20, choices=URGENZA_CHOICES, default='normale')
    descrizione   = models.TextField(verbose_name='Descrizione')
    data_preferita = models.DateField(null=True, blank=True, verbose_name='Data preferita')
    creata_il     = models.DateTimeField(default=timezone.now)
    gestita       = models.BooleanField(default=False, verbose_name='Presa in carico')

    class Meta:
        ordering = ['-creata_il']
        verbose_name = 'Richiesta intervento'
        verbose_name_plural = 'Richieste intervento'

    def __str__(self):
        return f"{self.cliente} — {self.tipo_problema} ({self.creata_il:%d/%m/%Y})"


class SegnalazioneInfestazione(models.Model):
    cliente     = models.ForeignKey(
        'anagrafica.Azienda', on_delete=models.CASCADE,
        related_name='segnalazioni',
    )
    filiale     = models.ForeignKey(
        'anagrafica.Filiale', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='segnalazioni',
        verbose_name='Sede',
    )
    luogo       = models.CharField(max_length=200, verbose_name='Luogo / area')
    infestante  = models.CharField(max_length=200, verbose_name='Infestante osservato')
    note        = models.TextField(blank=True)
    foto        = models.ImageField(upload_to='segnalazioni/', null=True, blank=True)
    creata_il   = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-creata_il']
        verbose_name = 'Segnalazione infestazione'
        verbose_name_plural = 'Segnalazioni infestazione'

    def __str__(self):
        return f"{self.cliente} — {self.infestante} ({self.creata_il:%d/%m/%Y})"


class FirmaDigitale(models.Model):
    ods         = models.OneToOneField(
        'servizi.ODS', on_delete=models.CASCADE,
        related_name='firma_digitale',
    )
    firma_svg   = models.TextField(verbose_name='Firma (base64 PNG)')
    firmato_il  = models.DateTimeField(default=timezone.now)
    firmato_da  = models.CharField(max_length=200, blank=True, verbose_name='Nome firmatario')

    class Meta:
        verbose_name = 'Firma digitale'

    def __str__(self):
        return f"Firma ODS {self.ods.numero}"
