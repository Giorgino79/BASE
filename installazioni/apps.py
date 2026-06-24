from django.apps import AppConfig


class InstallazioniConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installazioni'

    def ready(self):
        from core.sidebar import register_nav
        register_nav(
            section_key='servizi',
            section_label='Servizi',
            items=[
                {
                    'label': 'Installazioni',
                    'url': 'installazioni:installazione_list',
                    'icon': 'bi-pin-map',
                    'active_app': 'installazioni',
                },
            ],
            order=30,
        )
