from django.apps import AppConfig
from django.conf import settings

class BankingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'banking'

    def ready(self):
        if settings.DEBUG:
            return
        from . import scheduler
        scheduler.start()