from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from all_players.tasks import live_update, update_player_status1
from .models import Player
import os

scheduler = BackgroundScheduler()

def start_scheduler():
    """Starts the scheduler, ensuring no duplicate jobs run."""
    if os.environ.get("RUN_MAIN") == "true":  # Prevent double execution in Django
        print("🔄 Starting Scheduler...")

        # Run daily task once when server starts
        daily_task_wrapper()

        # Add Live Update Job (once every 24 hours)
        if not scheduler.get_job("live_update"):
            scheduler.add_job(
                live_update_wrapper,  # Wrapper function to handle the live update
                trigger=IntervalTrigger(hours=24),
                id="live_update",
                replace_existing=True,
            )
            print("✅ Scheduled: live_update (every 24 hours)")

        # Start the scheduler
        scheduler.start()
        print("✅ Scheduler started successfully!")

        # Debugging: Print all scheduled jobs
        for job in scheduler.get_jobs():
            print(f"📌 Job ID: {job.id}, Next run: {job.next_run_time}")

def daily_task_wrapper():
    """Runs the daily task, ensures no double execution."""
    print("🔄 Running daily task...")

    # Run live update task and schedule minute tasks if needed
    player_id, game_id, game_time = live_update()
    print(player_id, game_time, " jj")
    if player_id and game_time:
        print(f"📢 Game scheduled today at {game_time}")
        schedule_minute_task(player_id, game_id, game_time)

def live_update_wrapper():
    """Wrapper function for scheduled live updates."""
    print("🔄 Running scheduled live update...")
    player_id, game_id, game_time = live_update()
    if player_id and game_time:
        schedule_minute_task(player_id, game_id, game_time)

def schedule_minute_task(player_id, game_id, game_time):
    """Schedules a task that updates player status every 3 minutes for 8 hours."""
    print(f"⏳ Scheduling minute-based updates starting at {game_time}...")

    end_time = game_time + timedelta(hours=8)

    if not scheduler.get_job("minute_task"):
        scheduler.add_job(
            update_player_status1,
            trigger=IntervalTrigger(minutes=3, start_date=game_time, end_date=end_time),
            id="minute_task",
            args=[player_id, game_id],  # Pass necessary arguments
            replace_existing=True,
            max_instances=1,  # Prevent overlapping jobs
        )
        print("✅ Scheduled: minute_task (every 3 minutes for 8 hours)")

def stop_minute_task():
    """Stops the minute-based updates."""
    if scheduler.get_job("minute_task"):
        scheduler.remove_job("minute_task")
        print("🛑 Stopped minute task after 8 hours.")
