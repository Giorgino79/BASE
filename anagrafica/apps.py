from django.apps import AppConfig


class AnagraficaConfig(AppConfig):
    name = "anagrafica"

    def ready(self):
        try:
            from core.search import SearchRegistry
            from .models import Cliente, Fornitore

            SearchRegistry.register(
                model=Cliente,
                category='Anagrafica',
                icon='bi-person-badge',
                priority=9,
            )
            SearchRegistry.register(
                model=Fornitore,
                category='Anagrafica',
                icon='bi-truck',
                priority=8,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro ricerca anagrafica: {e}")
