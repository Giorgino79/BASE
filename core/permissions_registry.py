"""
Registry per gestione permissions sui modelli user-facing.

Questo modulo definisce quali modelli sono gestibili dagli admin
tramite il form di assegnazione permessi agli utenti.

IMPORTANTE:
- Solo i modelli registrati qui appariranno nel form permissions
- I modelli "di servizio" (Allegato, ModuloRegistry, etc.) NON vanno registrati
- Ogni nuovo modello user-facing VA REGISTRATO manualmente
"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType


class ModelPermissionRegistry:
    """
    Registry centralizzato per modelli gestibili con permissions.

    Pattern Singleton per garantire un unico registro globale.
    """

    _instance = None
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registry = {}
        return cls._instance

    def register(self, app_label, model_name, display_name=None, category=None, icon=None):
        """
        Registra un modello come gestibile con permissions.

        Args:
            app_label (str): Nome app Django (es. "users", "payroll")
            model_name (str): Nome modello lowercase (es. "user", "bustapaga")
            display_name (str): Nome visualizzato (es. "Utenti", "Buste Paga")
            category (str): Categoria per raggruppamento (es. "Gestione Personale")
            icon (str): Icona Bootstrap (es. "bi-people", "bi-cash-coin")

        Example:
            registry = ModelPermissionRegistry()
            registry.register(
                app_label="users",
                model_name="user",
                display_name="Utenti",
                category="Gestione Personale",
                icon="bi-people"
            )
        """
        key = f"{app_label}.{model_name}"

        # Verifica che il modello esista
        try:
            model_class = apps.get_model(app_label, model_name)
        except LookupError:
            raise ValueError(
                f"Modello {key} non trovato. Verifica app_label e model_name."
            )

        self._registry[key] = {
            "app_label": app_label,
            "model_name": model_name,
            "model_class": model_class,
            "display_name": display_name or model_class._meta.verbose_name_plural.title(),
            "category": category or app_label.title(),
            "icon": icon or "bi-file-earmark",
            "permissions": self._get_model_permissions(model_class),
        }

    def _get_model_permissions(self, model_class):
        """
        Ottiene i permessi Django standard per un modello.

        Returns:
            list: Lista di dict con codename, name, label
        """
        # Usa _meta invece di ContentType per evitare query al database
        app_label = model_class._meta.app_label
        model_name = model_class._meta.model_name
        permissions = []

        # Permessi CRUD standard Django
        for action, label in [
            ("add", "Creare"),
            ("view", "Visualizzare"),
            ("change", "Modificare"),
            ("delete", "Eliminare"),
        ]:
            codename = f"{action}_{model_name}"
            perm_name = f"{app_label}.{codename}"

            permissions.append(
                {
                    "codename": codename,
                    "full_name": perm_name,
                    "action": action,
                    "label": label,
                }
            )

        return permissions

    def get_registered_models(self):
        """
        Restituisce tutti i modelli registrati.

        Returns:
            dict: Dizionario {key: model_info}
        """
        return self._registry.copy()

    def get_models_by_category(self):
        """
        Restituisce modelli raggruppati per categoria.

        Returns:
            dict: {category: [model_info, ...]}
        """
        categorized = {}

        for model_info in self._registry.values():
            category = model_info["category"]
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(model_info)

        return categorized

    def is_registered(self, app_label, model_name):
        """Verifica se un modello è registrato"""
        key = f"{app_label}.{model_name}"
        return key in self._registry

    def get_model_info(self, app_label, model_name):
        """Ottiene informazioni su un modello registrato"""
        key = f"{app_label}.{model_name}"
        return self._registry.get(key)

    def unregister(self, app_label, model_name):
        """Rimuove un modello dal registro (usare con cautela!)"""
        key = f"{app_label}.{model_name}"
        if key in self._registry:
            del self._registry[key]


# ============================================================================
# REGISTRAZIONE MODELLI USER-FACING
# ============================================================================

def register_default_models():
    """
    Registra i modelli user-facing di default.
    Aggiungi nuove registrazioni quando installi nuovi moduli.
    """
    registry = ModelPermissionRegistry()

    # ========== APP: USERS ==========
    registry.register(
        app_label="users",
        model_name="user",
        display_name="Utenti / Dipendenti",
        category="👥 Users - Gestione Personale",
        icon="bi-people-fill",
    )

    registry.register(
        app_label="users",
        model_name="richiestaferie",
        display_name="Richieste Ferie",
        category="👥 Users - Gestione Personale",
        icon="bi-calendar-check",
    )

    registry.register(
        app_label="users",
        model_name="richiestapermesso",
        display_name="Richieste Permessi",
        category="👥 Users - Gestione Personale",
        icon="bi-clock-history",
    )

    registry.register(
        app_label="users",
        model_name="letterarichiamo",
        display_name="Lettere di Richiamo",
        category="👥 Users - Gestione Personale",
        icon="bi-exclamation-triangle-fill",
    )

    registry.register(
        app_label="users",
        model_name="giornatalavorativa",
        display_name="Giornate Lavorative",
        category="👥 Users - Gestione Personale",
        icon="bi-calendar3",
    )

    registry.register(
        app_label="users",
        model_name="timbratura",
        display_name="Timbrature",
        category="👥 Users - Gestione Personale",
        icon="bi-stopwatch",
    )


    # Aggiungi qui le registrazioni dei moduli futuri.
# UTILITY FUNCTIONS
# ============================================================================


def get_user_model_permissions(user):
    """
    Ottiene i permessi dell'utente sui modelli registrati.

    Args:
        user: Istanza User

    Returns:
        dict: {
            'app_label.model_name': {
                'can_add': bool,
                'can_view': bool,
                'can_change': bool,
                'can_delete': bool,
            }
        }
    """
    registry = ModelPermissionRegistry()
    user_perms = {}

    for key, model_info in registry.get_registered_models().items():
        model_class = model_info["model_class"]

        user_perms[key] = {
            "can_add": user.has_perm(f"{model_info['app_label']}.add_{model_info['model_name']}"),
            "can_view": user.has_perm(f"{model_info['app_label']}.view_{model_info['model_name']}"),
            "can_change": user.has_perm(f"{model_info['app_label']}.change_{model_info['model_name']}"),
            "can_delete": user.has_perm(f"{model_info['app_label']}.delete_{model_info['model_name']}"),
        }

    return user_perms


def get_registry():
    """Helper per ottenere l'istanza del registry"""
    return ModelPermissionRegistry()
