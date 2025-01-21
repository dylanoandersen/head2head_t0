from django.apps import AppConfig


class AllPlayersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'all_players'

    # Start function when server starts
    def ready(self):
        print("AppConfig ready method executed.")
        from .scheduler import start_scheduler
        start_scheduler()


