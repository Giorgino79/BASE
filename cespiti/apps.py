from django.apps import AppConfig


class CespitiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cespiti"
    label = "cespiti"
    verbose_name = "Cespiti"

    def ready(self):
        self._register_sidebar()
        self._register_calendario()

    def _register_sidebar(self):
        from core.sidebar import register_nav
        register_nav("cespiti", "Cespiti", [
            {"label": "Cespiti", "url": "cespiti:dashboard", "icon": "bi-truck", "active_app": "cespiti"},
        ], order=50)

    def _register_calendario(self):
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import (
                get_manutenzioni_programmate,
                get_revisioni_in_scadenza,
                get_assicurazioni_in_scadenza,
                get_scadenze_documenti_stabilimenti,
                get_scadenze_servizi_stabilimenti,
            )
            CalendarioRegistry.register(
                name='cespiti_manutenzioni',
                provider_func=get_manutenzioni_programmate,
                category='Cespiti',
                description='Manutenzioni programmate',
                color='#6f42c1',
                priority=30,
            )
            CalendarioRegistry.register(
                name='cespiti_revisioni',
                provider_func=get_revisioni_in_scadenza,
                category='Cespiti',
                description='Revisioni automezzi',
                color='#0d6efd',
                priority=31,
            )
            CalendarioRegistry.register(
                name='cespiti_assicurazioni',
                provider_func=get_assicurazioni_in_scadenza,
                category='Cespiti',
                description='Assicurazioni automezzi',
                color='#198754',
                priority=32,
            )
            CalendarioRegistry.register(
                name='cespiti_documenti_stabilimenti',
                provider_func=get_scadenze_documenti_stabilimenti,
                category='Cespiti',
                description='Scadenze documenti stabilimenti',
                color='#dc3545',
                priority=33,
            )
            CalendarioRegistry.register(
                name='cespiti_servizi_stabilimenti',
                provider_func=get_scadenze_servizi_stabilimenti,
                category='Cespiti',
                description='Scadenze servizi stabilimenti',
                color='#fd7e14',
                priority=34,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario cespiti: {e}")
