from django.apps import AppConfig


class ServiziConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'servizi'

    def ready(self):
        from core.sidebar import register_nav
        register_nav(
            section_key='servizi',
            section_label='Servizi',
            items=[
                {
                    'label': 'Servizi',
                    'url': 'servizi:dashboard',
                    'icon': 'bi-clipboard-check',
                    'active_app': 'servizi',
                },
            ],
            order=30,
        )

        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import get_ods_eventi
            CalendarioRegistry.register(
                name='ods',
                provider_func=get_ods_eventi,
                category='Servizi',
                description='Ordini di Servizio programmati',
                color='#fd7e14',
                priority=30,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario ODS: {e}")
