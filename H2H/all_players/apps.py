from django.apps import AppConfig
import os


class AllPlayersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'all_players'

    # Start function when server starts
    def ready(self):
        if os.environ.get("RUN_MAIN") == "true":  # Only execute in the main process
            from .scheduler import start_scheduler
            start_scheduler()


