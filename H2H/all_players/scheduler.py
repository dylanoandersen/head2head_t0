from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from all_players.tasks import live_update, update_player_status1

scheduler = BackgroundScheduler()

def start_scheduler():
    # Schedule the daily task to run once a day
    daily_task_wrapper()
    print("Starting scheduler...")
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
    output, ouput1 = live_update()  # Call your existing daily task
    if output:  # If the daily task returns something meaningful
        schedule_minute_task(output, ouput1)

def schedule_minute_task(output):
    print(f"Scheduling minute task for: {output}")
    # Schedule the minute task to run every minute for 24 hours
    scheduler.add_job(
        update_player_status1,
        trigger=IntervalTrigger(minutes=1),
        id="minute_task",
        args=[output],  # Pass any arguments needed for the minute task
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
