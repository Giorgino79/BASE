from django.apps import AppConfig


class AutomezziConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "automezzi"
    label = "automezzi"
    verbose_name = "Automezzi"

    def ready(self):
        self._register_sidebar()
        self._register_calendario()

    def _register_sidebar(self):
        from core.sidebar import register_nav
        register_nav("automezzi", "Automezzi", [
            {"label": "Automezzi", "url": "automezzi:dashboard", "icon": "bi-truck", "active_app": "automezzi"},
        ], order=51)

    def _register_calendario(self):
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import (
                get_manutenzioni_programmate,
                get_revisioni_in_scadenza,
                get_assicurazioni_in_scadenza,
            )
            CalendarioRegistry.register(
                name='automezzi_manutenzioni',
                provider_func=get_manutenzioni_programmate,
                category='Automezzi',
                description='Manutenzioni programmate',
                color='#6f42c1',
                priority=30,
            )
            CalendarioRegistry.register(
                name='automezzi_revisioni',
                provider_func=get_revisioni_in_scadenza,
                category='Automezzi',
                description='Revisioni automezzi',
                color='#0d6efd',
                priority=31,
            )
            CalendarioRegistry.register(
                name='automezzi_assicurazioni',
                provider_func=get_assicurazioni_in_scadenza,
                category='Automezzi',
                description='Assicurazioni automezzi',
                color='#198754',
                priority=32,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario automezzi: {e}")
