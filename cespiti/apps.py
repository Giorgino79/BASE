from django.apps import AppConfig


class CespitiConfig(AppConfig):
    """App ritirata dal catalogo prodotto il 26/08/2026 — vedi models.py.
    Nessuna registrazione sidebar/calendario: non e' piu' un'app
    user-facing, resta solo come ancora storica per le migrazioni."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cespiti"
    label = "cespiti"
    verbose_name = "Cespiti (ritirata)"
