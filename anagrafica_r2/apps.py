from django.apps import AppConfig


class AnagraficaR2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'anagrafica_r2'
    label = 'anagrafica'
    verbose_name = 'Anagrafica Clienti'

    def ready(self):
        from django.db.models.signals import post_save
        from django.dispatch import receiver

        @receiver(post_save, sender='anagrafica.Azienda')
        def crea_sede_default(sender, instance, created, **kwargs):
            """
            Se sede_unica=True crea automaticamente una Filiale 'Sede' che replica
            l'indirizzo dell'Azienda, così il cliente appare subito come luogo
            di espletazione del servizio senza dover inserire sedi separate.
            """
            if not instance.sede_unica:
                return
            if created and not instance.filiali.exists():
                from anagrafica_r2.models import Filiale
                Filiale.objects.create(
                    cliente=instance,
                    nome="Sede",
                    tipo_sede="altro",
                    indirizzo=instance.indirizzo,
                    citta=instance.citta,
                    zona=instance.zona,
                    cap=instance.cap,
                    provincia=instance.provincia,
                    attivo=True,
                )

        from core.sidebar import register_nav
        register_nav(
            section_key='anagrafica',
            section_label='Anagrafica',
            items=[
                {
                    'label': 'Anagrafica',
                    'url': 'anagrafica:dashboard',
                    'icon': 'bi-building',
                    'active_app': 'anagrafica',
                },
            ],
            order=10,
        )

        try:
            from whatsapp.contact_sources import register_source

            def _contatti_aziende():
                from .models import Azienda
                return [(a.telefono, str(a)) for a in Azienda.objects.filter(attivo=True).exclude(telefono="")]

            def _contatti_privati():
                from .models import Privato
                return [(p.telefono, str(p)) for p in Privato.objects.filter(attivo=True).exclude(telefono="")]

            def _contatti_fornitori():
                from .models import Fornitore
                return [(f.telefono, str(f)) for f in Fornitore.objects.exclude(telefono="")]

            register_source("aziende", "Tutte le aziende attive", _contatti_aziende)
            register_source("privati", "Tutti i privati attivi", _contatti_privati)
            register_source("fornitori", "Tutti i fornitori", _contatti_fornitori)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro contatti whatsapp: {e}")
