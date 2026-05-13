"""
Sistema di ricerca globale - SearchRegistry
Gestisce la registrazione e ricerca di model in tutto il sistema.
"""

from django.apps import apps


class SearchRegistry:
    """
    Registry centrale per tutti i model ricercabili del sistema.

    Ogni app può registrare i propri model nel metodo ready() di apps.py.

    Esempio di utilizzo:
        # anagrafica/apps.py
        from core.search import SearchRegistry

        def ready(self):
            from .models import Cliente

            SearchRegistry.register(
                model=Cliente,
                category='Anagrafica',
                icon='bi-person-badge',
                priority=10
            )
    """

    _registry = {}

    @classmethod
    def register(cls, model, category, icon="bi-file-earmark", priority=5):
        """
        Registra un model come ricercabile.

        Args:
            model: classe del model Django
            category: categoria di appartenenza (es. 'Anagrafica', 'Vendite')
            icon: classe icona Bootstrap Icons (es. 'bi-person-badge')
            priority: priorità nei risultati (0-10, default 5)

        Returns:
            None
        """
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"

        cls._registry[model_key] = {
            "model": model,
            "category": category,
            "icon": icon,
            "priority": priority,
            "verbose_name": model._meta.verbose_name,
            "verbose_name_plural": model._meta.verbose_name_plural,
        }

    @classmethod
    def unregister(cls, model):
        """
        Rimuove un model dal registry.

        Args:
            model: classe del model Django
        """
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        if model_key in cls._registry:
            del cls._registry[model_key]

    @classmethod
    def get_all_models(cls):
        """
        Restituisce tutti i model registrati.

        Returns:
            list: Lista di classi model
        """
        return [entry["model"] for entry in cls._registry.values()]

    @classmethod
    def get_model_info(cls, model):
        """
        Restituisce le informazioni di un model registrato.

        Args:
            model: classe del model Django

        Returns:
            dict: Dizionario con info del model o None se non registrato
        """
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        return cls._registry.get(model_key)

    @classmethod
    def search_all(cls, query, max_results_per_model=5):
        """
        Esegue ricerca in tutti i model registrati.

        Args:
            query: stringa di ricerca
            max_results_per_model: numero massimo risultati per model

        Returns:
            list: Lista di dizionari con risultati raggruppati per categoria
        """
        if not query or not query.strip():
            return []

        results_by_category = {}

        # Itera tutti i model registrati
        for model_key, model_info in cls._registry.items():
            model = model_info["model"]
            category = model_info["category"]

            # Esegue ricerca nel model
            try:
                model_results = model.search(query)

                # Se ci sono risultati, li aggiungi alla categoria
                if model_results.exists():
                    if category not in results_by_category:
                        results_by_category[category] = []

                    for obj in model_results:
                        results_by_category[category].append(
                            {
                                "id": obj.pk,
                                "title": obj.get_search_result_display(),
                                "subtitle": str(model._meta.verbose_name),
                                "url": obj.get_absolute_url(),
                                "icon": model_info["icon"],
                                "priority": model_info["priority"],
                            }
                        )
            except Exception as e:
                # Log error ma continua con altri model
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Errore ricerca in {model_key}: {str(e)}")
                continue

        # Converte dizionario in lista ordinata
        results = []
        for category, items in results_by_category.items():
            # Ordina items per priority (alta -> bassa)
            items.sort(key=lambda x: x["priority"], reverse=True)

            results.append(
                {"category": category, "items": items[:max_results_per_model]}
            )

        # Ordina categorie alfabeticamente
        results.sort(key=lambda x: x["category"])

        return results

    @classmethod
    def is_registered(cls, model):
        """
        Verifica se un model è registrato.

        Args:
            model: classe del model Django

        Returns:
            bool: True se registrato, False altrimenti
        """
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        return model_key in cls._registry

    @classmethod
    def get_registered_count(cls):
        """
        Restituisce il numero di model registrati.

        Returns:
            int: Numero di model nel registry
        """
        return len(cls._registry)

    @classmethod
    def clear(cls):
        """
        Svuota il registry (utile per testing).
        """
        cls._registry = {}
