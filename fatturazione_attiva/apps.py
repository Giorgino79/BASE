from django.apps import AppConfig


class FatturazioneAttivaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fatturazione_attiva"
    verbose_name = "Fatturazione Attiva"

    def ready(self):
        from core.sidebar import register_nav
        register_nav(
            section_key="fatturazione",
            section_label="Fatturazione",
            items=[
                {
                    "label": "Fatturazione",
                    "url":   "fatturazione_attiva:dashboard",
                    "icon":  "bi-receipt",
                    "active_app": "fatturazione_attiva",
                    "active_url_contains": ["dashboard", "ricerca", "fatture", "da-incassare"],
                },
            ],
            order=35,
        )
