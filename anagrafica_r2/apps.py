from django.apps import AppConfig


class AnagraficaR2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'anagrafica_r2'
    label = 'anagrafica'
    verbose_name = 'Anagrafica Clienti'

    def ready(self):
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
