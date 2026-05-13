from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Users - Gestione Utenti"

    def ready(self):
        """
        Codice eseguito quando l'app è pronta.

        Registra model User nel SearchRegistry per ricerca globale.
        Importa signals per creazione automatica EmailConfiguration.
        Registra provider ferie/permessi nel CalendarioRegistry.
        """
        from core.search import SearchRegistry
        from .models import User

        # Importa signals (creazione automatica EmailConfiguration)
        from . import signals  # noqa: F401

        # Registra User nel sistema ricerca globale
        SearchRegistry.register(
            model=User, category="Users", icon="bi-person-circle", priority=10
        )

        # Registra provider calendario aziendale
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import get_ferie_approvate, get_permessi_approvati

            CalendarioRegistry.register(
                name='ferie_approvate',
                provider_func=get_ferie_approvate,
                permission='users.approva_ferie',
                category='HR',
                description='Ferie approvate di tutti i dipendenti',
                color='#28a745',
                priority=10,
            )
            CalendarioRegistry.register(
                name='permessi_approvati',
                provider_func=get_permessi_approvati,
                permission='users.approva_ferie',
                category='HR',
                description='Permessi orari approvati di tutti i dipendenti',
                color='#17a2b8',
                priority=11,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registrazione CalendarioRegistry (users): {e}")
