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
            """Crea automaticamente una filiale 'Sede' se l'Azienda non ne ha ancora."""
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
                {
                    'label': 'Privati',
                    'url': 'anagrafica:privato_list',
                    'icon': 'bi-person',
                    'active_app': 'anagrafica',
                    'active_url_contains': 'privati',
                },
            ],
            order=10,
        )
