from django.apps import AppConfig


class InstallazioniConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installazioni'

    def ready(self):
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import get_installazioni_eventi

            CalendarioRegistry.register(
                name='installazioni',
                provider_func=get_installazioni_eventi,
                category='Installazioni',
                description='Installazioni non ancora completate',
                color='#20c997',
                priority=32,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario installazioni: {e}")
