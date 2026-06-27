from django.apps import AppConfig


class InstallazioniConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installazioni'

    def ready(self):
        pass
