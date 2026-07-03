from django.apps import AppConfig


class ContabilitaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contabilita"
    verbose_name = "Contabilità"

    def ready(self):
        import contabilita.signals  # noqa: F401

        from core.sidebar import register_nav
        register_nav(
            section_key="contabilita",
            section_label="Contabilità",
            items=[
                {
                    "label": "Contabilità",
                    "url":   "contabilita:dashboard",
                    "icon":  "bi-journal-text",
                    "active_app": "contabilita",
                },
            ],
            order=40,
        )
