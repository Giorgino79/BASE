from django.apps import AppConfig

class CorrispondenzaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'corrispondenza'
    verbose_name = 'Corrispondenza'

    def ready(self):
        pass
