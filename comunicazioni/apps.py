from django.apps import AppConfig


class ComunicazioniConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comunicazioni'

    def ready(self):
        pass
