"""
Pulizia dei file allegati ai promemoria.

Django cancella la riga sul DB ma NON il file sullo storage (filesystem in
locale, Cloudinary in produzione): senza questi segnali gli allegati dei
promemoria eliminati resterebbero lì per sempre.
"""
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Promemoria


@receiver(post_delete, sender=Promemoria)
def elimina_allegato_su_delete(sender, instance, **kwargs):
    """Promemoria eliminato → l'allegato sparisce definitivamente."""
    if instance.allegato:
        instance.allegato.delete(save=False)


@receiver(pre_save, sender=Promemoria)
def elimina_allegato_su_sostituzione(sender, instance, **kwargs):
    """Allegato sostituito o rimosso in modifica → cancella il vecchio file."""
    if not instance.pk:
        return
    try:
        vecchio = Promemoria.objects.get(pk=instance.pk).allegato
    except Promemoria.DoesNotExist:
        return
    if vecchio and vecchio.name != instance.allegato.name:
        vecchio.delete(save=False)
