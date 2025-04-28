import random
from django.db import models
from User.models import Matchup

# Define the list of positions
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF", "FLX"]

def assign_random_positions():
    """
    This script checks for Matchup entries with NULL values in the 'position' column
    and assigns a random position from the predefined list.
    """
    try:
        null_position_matchups = Matchup.objects.filter(position__isnull=True)

        if not null_position_matchups.exists():
            print("No matchups with NULL positions found.")
            return

        print(f"Found {null_position_matchups.count()} matchups with NULL positions.")

        for matchup in null_position_matchups:
            random_position = random.choice(POSITIONS)
            matchup.position = random_position
            matchup.save()
            print(f"Assigned position '{random_position}' to matchup ID {matchup.id}.")

        print("All NULL positions have been updated successfully.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    assign_random_positions()