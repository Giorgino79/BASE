from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analysis"
    verbose_name = "Analisi"

    def ready(self):
        from core.sidebar import register_nav
        register_nav(
            "analysis",
            "Analisi",
            [
                {
                    "label": "Analisi",
                    "url": "analysis:dashboard",
                    "icon": "bi-bar-chart-line",
                    "active_app": "analysis",
                    "staff_only": True,
                }
            ],
            order=90,
        )
