from django.apps import AppConfig


class MagazzinoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'magazzino'
    label = 'magazzino'
    verbose_name = 'Magazzino'

    def ready(self):
        from core.sidebar import register_nav
        register_nav("magazzino", "Magazzino", [
            {"label": "Magazzino", "url": "magazzino:dashboard", "icon": "bi-boxes", "active_app": "magazzino"},
        ], order=65)
