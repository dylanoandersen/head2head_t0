from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from all_players.tasks import live_update, update_player_status1
from .models import Player

scheduler = BackgroundScheduler()

def start_scheduler():
    # Schedule the daily task to run once a day
    daily_task_wrapper()
    print("Starting scheduler...")
    Player.objects.filter(firstName='').delete()

    scheduler.add_job(
        daily_task_wrapper,  # Wrapper function to handle output
        trigger=IntervalTrigger(hours=24),  # Run every 24 hours
        id="live_update",
        replace_existing=True,
    )
    scheduler.start()
    for job in scheduler.get_jobs():
        print(f"- {job.id}: Next run at {job.next_run_time}")

def daily_task_wrapper():
    print("Running daily task...")
    player_id, game_id, game_time = live_update()  # Call your existing daily task
    if player_id:  # If the daily task returns something meaningful
        schedule_minute_task(player_id, game_id)

def schedule_minute_task(player_id, game_id, game_time):
    print(f"Scheduling minute task for: {player_id}, {game_id}, at {game_time}")
    end_time = game_time + timedelta(hours=8)
    scheduler.add_job(
        update_player_status1,
        trigger=IntervalTrigger(minutes=1, start_date=game_time, end_date=end_time),
        id="minute_task",
        args=[player_id, game_id],  # Pass any arguments needed for the minute task
        replace_existing=True,
        max_instances=1,  # Avoid overlapping jobs
    )
    # Optionally stop this job after 24 hours
    scheduler.add_job(
        stop_minute_task,
        trigger=IntervalTrigger(hours=24),
        id="stop_minute_task",
        replace_existing=True,
    )

def stop_minute_task():
    print("Stopping minute task after 24 hours...")
    scheduler.remove_job("minute_task")
