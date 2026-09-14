from django.apps import AppConfig


class StabilimentiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stabilimenti"
    label = "stabilimenti"
    verbose_name = "Stabilimenti"

    def ready(self):
        self._register_sidebar()
        self._register_calendario()

    def _register_sidebar(self):
        from core.sidebar import register_nav
        register_nav("stabilimenti", "Stabilimenti", [
            {"label": "Stabilimenti", "url": "stabilimenti:dashboard", "icon": "bi-building-gear", "active_app": "stabilimenti"},
        ], order=49)

    def _register_calendario(self):
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import (
                get_scadenze_documenti_stabilimenti,
                get_scadenze_servizi_stabilimenti,
            )
            CalendarioRegistry.register(
                name='stabilimenti_documenti',
                provider_func=get_scadenze_documenti_stabilimenti,
                category='Stabilimenti',
                description='Scadenze documenti stabilimenti',
                color='#dc3545',
                priority=33,
            )
            CalendarioRegistry.register(
                name='stabilimenti_servizi',
                provider_func=get_scadenze_servizi_stabilimenti,
                category='Stabilimenti',
                description='Scadenze servizi stabilimenti',
                color='#fd7e14',
                priority=34,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario stabilimenti: {e}")
