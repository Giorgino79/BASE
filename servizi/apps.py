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
                {
                    'label': 'La mia giornata',
                    'url': 'servizi:dashboard_tecnico',
                    'icon': 'bi-person-workspace',
                    'active_app': 'servizi',
                    'active_url_contains': 'tecnico',
                },
            ],
            order=30,
        )

        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import get_ods_eventi, get_condomini_eventi
            CalendarioRegistry.register(
                name='ods',
                provider_func=get_ods_eventi,
                category='Servizi',
                description='Ordini di Servizio programmati',
                color='#fd7e14',
                priority=30,
            )
            CalendarioRegistry.register(
                name='condomini',
                provider_func=get_condomini_eventi,
                category='Servizi',
                description='Condomini da espletare',
                color='#0d6efd',
                priority=31,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario ODS: {e}")
