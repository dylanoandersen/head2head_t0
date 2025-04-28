from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from all_players.tasks import live_update, update_player_status1
from .models import Player
import os

scheduler = BackgroundScheduler()

def start_scheduler():
    """Starts the scheduler, ensuring no duplicate jobs run."""
    print(" Starting Scheduler...")

    daily_task_wrapper()

    if not scheduler.get_job("live_update"):
        scheduler.add_job(
            live_update_wrapper,
            trigger=IntervalTrigger(hours=24),
            id="live_update",
            replace_existing=True,
        )
        print(" Scheduled: live_update (every 24 hours)")

    scheduler.start()
    print(" Scheduler started successfully!")

    for job in scheduler.get_jobs():
        print(f" Job ID: {job.id}, Next run: {job.next_run_time}")

def daily_task_wrapper():
    """Runs the daily task, ensures no double execution."""
    print(" Running daily task...")

    game_dict, game_time = live_update()
    print(game_dict, game_time, " jj")
    if game_dict and game_time:
        print(f" Game scheduled today at {game_time}")
        schedule_minute_task(game_dict, game_time)

def live_update_wrapper():
    """Wrapper function for scheduled live updates."""
    print(" Running scheduled live update...")
    game_dict, game_time = live_update()
    if game_dict and game_time:
        schedule_minute_task(game_dict, game_time)

def schedule_minute_task(game_dict, game_time):
    """Schedules a task that updates player status every 3 minutes for 8 hours."""
    print(f" Scheduling minute-based updates starting at {game_time}...")

    end_time = game_time + timedelta(hours=8)

    if not scheduler.get_job("minute_task"):
        scheduler.add_job(
            update_player_status1,
            trigger=IntervalTrigger(minutes=60, start_date=game_time, end_date=end_time),
            id="minute_task",
            args=[game_dict],
            replace_existing=True,
            max_instances=1,
        )
        print(" Scheduled: minute_task (every 3 minutes for 8 hours)")

def stop_minute_task():
    """Stops the minute-based updates."""
    if scheduler.get_job("minute_task"):
        scheduler.remove_job("minute_task")
        print(" Stopped minute task after 8 hours.")
