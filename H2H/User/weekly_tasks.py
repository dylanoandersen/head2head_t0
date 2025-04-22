from datetime import datetime
from django.db import transaction
from User.models import Week, Bet, Matchup, Player_Stats

def weekly_update():
    today = datetime.now()
    if today.weekday() == 2:  # Wednesday
        week_instance = Week.objects.first()
        if not week_instance.updated_on_wednesday:
            with transaction.atomic():
                # Increment the week
                week_instance.week += 1
                week_instance.updated_on_wednesday = True
                week_instance.save()

                # Resolve bets
                resolve_all_bets(week_instance.week)

    else:
        # Reset the flag on other days
        week_instance = Week.objects.first()
        if week_instance.updated_on_wednesday:
            week_instance.updated_on_wednesday = False
            week_instance.save()

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