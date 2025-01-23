from django.apps import AppConfig


class AllPlayersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'all_players'

    # Start function when server starts
    def ready(self):
        from django.core.signals import request_finished
        from .scheduler import start_scheduler

        # Connect to the `request_finished` signal to delay starting
        request_finished.connect(start_scheduler)


