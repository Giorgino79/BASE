"""
Sistema di registrazione per eventi del calendario aziendale.

Permette alle app di registrare event providers che generano eventi
per il calendario con controllo permessi integrato.

Uso in apps.py di ogni app:

    def ready(self):
        try:
            from core.calendario_registry import CalendarioRegistry
            from .calendario_providers import get_miei_eventi

            CalendarioRegistry.register(
                name='miei_eventi',
                provider_func=get_miei_eventi,
                permission='mia_app.view_miomodello',
                category='La Mia Categoria',
                description='Descrizione eventi',
                color='#007bff',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registro calendario: {e}")
"""

from typing import Callable, Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CalendarioRegistry:
    """
    Registry per event providers del calendario aziendale.

    Ogni provider è una funzione (user, start_date, end_date) → lista dict FullCalendar.
    """

    _providers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        provider_func: Callable,
        permission: Optional[str] = None,
        category: str = 'Altri',
        description: str = '',
        color: Optional[str] = None,
        priority: int = 50
    ):
        """
        Registra un event provider.

        Args:
            name: Nome univoco del provider
            provider_func: Funzione (user, start_date, end_date) → list[dict]
            permission: Permesso Django richiesto. Se None, visibile a tutti.
            category: Categoria per raggruppare i provider
            description: Descrizione breve
            color: Colore default eventi (hex)
            priority: Ordine rendering (più basso = prima)
        """
        if name in cls._providers:
            logger.warning(f"Provider '{name}' già registrato. Verrà sovrascritto.")

        cls._providers[name] = {
            'name': name,
            'func': provider_func,
            'permission': permission,
            'category': category,
            'description': description,
            'color': color,
            'priority': priority,
        }
        logger.info(f"Provider calendario '{name}' registrato (categoria: {category})")

    @classmethod
    def unregister(cls, name: str):
        """Rimuove un provider dal registry."""
        if name in cls._providers:
            del cls._providers[name]

    @classmethod
    def get_events_for_user(
        cls,
        user,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[str]] = None,
        providers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera tutti gli eventi per un utente con controllo permessi.

        Args:
            user: Utente Django
            start_date: Data inizio filtro
            end_date: Data fine filtro
            categories: Filtra per categorie (None = tutte)
            providers: Filtra per nome provider (None = tutti)

        Returns:
            Lista eventi formato FullCalendar
        """
        if not user or not user.is_authenticated:
            return []

        all_events = []

        sorted_providers = sorted(
            cls._providers.values(),
            key=lambda p: p['priority']
        )

        for provider in sorted_providers:
            # Filtro per provider name esplicito
            if providers and provider['name'] not in providers:
                continue

            # Filtro per categoria
            if categories and provider['category'] not in categories:
                continue

            # Controllo permessi Django
            permission = provider['permission']
            if permission and not user.has_perm(permission):
                continue

            try:
                events = provider['func'](user, start_date, end_date)

                if provider['color']:
                    for event in events:
                        if 'color' not in event:
                            event['color'] = provider['color']

                for event in events:
                    event.setdefault('extendedProps', {})
                    event['extendedProps']['provider'] = provider['name']
                    event['extendedProps']['category'] = provider['category']

                all_events.extend(events)

            except Exception as e:
                logger.error(f"Errore nel provider '{provider['name']}': {e}", exc_info=True)
                continue

        return all_events

    @classmethod
    def get_categories(cls) -> List[str]:
        """Restituisce tutte le categorie registrate."""
        return sorted(set(p['category'] for p in cls._providers.values()))

    @classmethod
    def get_providers_info(cls, user=None) -> List[Dict[str, Any]]:
        """
        Info sui provider, opzionalmente filtrate per permessi utente.
        """
        result = []
        for provider in cls._providers.values():
            if user:
                perm = provider['permission']
                if perm and not user.has_perm(perm):
                    continue
            result.append({
                'name': provider['name'],
                'category': provider['category'],
                'description': provider['description'],
                'color': provider['color'],
            })
        return result

    @classmethod
    def clear(cls):
        """Pulisce tutti i provider (uso nei test)."""
        cls._providers.clear()
