from django.apps import AppConfig
#from datetime import datetime
#from django.db import transaction
#from User.models import Week, Bet, Matchup, Player_Stats  # Import necessary models

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'User'

    def ready(self):
        # Import the weekly_update function and call it
        import User.signals
        
       # from .weekly_tasks import weekly_update
     #  weekly_update()
