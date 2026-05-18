# pyrefly: ignore [missing-import]
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    # Add this ready function to wake up the signals
    def ready(self):
        # pyrefly: ignore [missing-import]
        import core.signals
