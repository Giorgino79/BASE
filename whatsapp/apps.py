from django.apps import AppConfig


class WhatsappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whatsapp"
    verbose_name = "WhatsApp"

    def ready(self):
        from core.sidebar import register_nav
        register_nav("whatsapp", "WhatsApp", [
            {"label": "WhatsApp", "url": "whatsapp:dashboard",
             "icon": "bi-whatsapp", "active_app": "whatsapp"},
        ], order=90)
