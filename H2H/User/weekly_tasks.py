from datetime import datetime
from django.db import transaction
from User.models import Week, Bet, Matchup, Player_Stats

from datetime import datetime
from django.db import transaction
from User.models import Week, Bet, Matchup, Player_Stats

def weekly_update():
    today = datetime.now()
    print(f"[DEBUG] Today is: {today}, Weekday: {today.weekday()}")

    # Ensure the Week object exists
    week_instance, created = Week.objects.get_or_create(id=1, defaults={"week": 1, "updated_on_wednesday": False})
    print(f"[DEBUG] Week instance: {week_instance}, Created: {created}")

    if today.weekday() == 2:  # Wednesday
        if not week_instance.updated_on_wednesday:
            print("[DEBUG] Updating week and setting updated_on_wednesday to True.")
            with transaction.atomic():
                week_instance.week += 1
                week_instance.updated_on_wednesday = True
                print(f"[DEBUG] Before save: updated_on_wednesday = {week_instance.updated_on_wednesday}")
                week_instance.save()
                week_instance.refresh_from_db()  # Ensure the object is reloaded
                print(f"[DEBUG] After refresh: updated_on_wednesday = {week_instance.updated_on_wednesday}")

                # Resolve bets
                resolve_all_bets(week_instance.week)
        else:
            print("[DEBUG] Week already updated for this Wednesday.")
    else:
        if week_instance.updated_on_wednesday:
            print("[DEBUG] Resetting updated_on_wednesday to False.")
            week_instance.updated_on_wednesday = False
            print(f"[DEBUG] Before save: updated_on_wednesday = {week_instance.updated_on_wednesday}")
            week_instance.save()
            week_instance.refresh_from_db()  # Ensure the object is reloaded
            print(f"[DEBUG] After refresh: updated_on_wednesday = {week_instance.updated_on_wednesday}")

            
def resolve_all_bets(current_week):
    bets = Bet.objects.filter(resolved=False, matchup__week=current_week)
    for bet in bets:
        # Logic to resolve bets based on player stats
        bet1, bet2 = Bet.objects.filter(matchup=bet.matchup)
        bet1_stats = Player_Stats.objects.get(player_id=bet1.player_id, week=current_week)
        bet2_stats = Player_Stats.objects.get(player_id=bet2.player_id, week=current_week)

        if bet1_stats.total_fantasy_points > bet2_stats.total_fantasy_points:
            bet1.winner = bet1.team
            bet2.winner = bet1.team
        else:
            bet1.winner = bet2.team
            bet2.winner = bet2.team

        bet1.resolved = True
        bet2.resolved = True
        bet1.save()
        bet2.save()