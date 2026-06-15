from django.apps import AppConfig


class FatturazioneAttivaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fatturazione_attiva"
    verbose_name = "Fatturazione Attiva"

    def ready(self):
        pass
