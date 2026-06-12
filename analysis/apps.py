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
                    "label": "Dashboard",
                    "url": "analysis:dashboard",
                    "icon": "bi-bar-chart-line",
                    "active_app": "analysis",
                    "active_url_contains": "analysis",
                    "staff_only": True,
                },
                {
                    "label": "Ricavi e Consumi",
                    "url": "analysis:costi_servizi",
                    "icon": "bi-table",
                    "active_app": "analysis",
                    "active_url_contains": "costi-servizi",
                    "staff_only": True,
                },
            ],
            order=90,
        )
