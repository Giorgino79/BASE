from django.apps import AppConfig


class AcquistiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'acquisti'
    label = 'acquisti'
    verbose_name = 'Acquisti'

    def ready(self):
        from core.sidebar import register_nav
        register_nav("acquisti", "Acquisti", [
            {"label": "Acquisti", "url": "acquisti:dashboard", "icon": "bi-cart3", "active_app": "acquisti"},
        ], order=60)
