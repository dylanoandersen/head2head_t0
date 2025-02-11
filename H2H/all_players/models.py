from django.db import models

class Player(models.Model):
    id = models.CharField(max_length=20, primary_key=True) 
    status = models.CharField(max_length=100, default='0')
    position = models.CharField(max_length=100, default='0')
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    team = models.CharField(max_length=100, default='0')
    location = models.CharField(max_length=100, default='0') 
    weight = models.FloatField(default=0)
    displayHeight = models.CharField(default=0, max_length=100)
    age = models.IntegerField(default=0)
    experience = models.CharField(max_length=100, default='0')
    jersey = models.IntegerField(default=-1)

    def __str__(self):
        return f"{self.id} {self.firstName} {self.lastName}"

class Player_Stats(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    firstName = models.CharField(max_length=20, default='0')
    lastName = models.CharField(max_length=20, default='0')
    game_id = models.CharField(max_length=20, default='0')
    week = models.IntegerField(default=0)
    pass_att = models.IntegerField(default=0)
    completions = models.IntegerField(default=0)
    completions_perc = models.FloatField(default=0)
    pass_yards = models.IntegerField(default=0)
    avg_pass_yards_completions = models.FloatField(default=0)
    pass_tds = models.IntegerField(default=0)
    ints = models.IntegerField(default=0)
    sacks = models.IntegerField(default=0)
    catches = models.IntegerField(default=0)
    targets = models.IntegerField(default=0)
    avg_recieving_yards_perCatch = models.FloatField(default=0)
    receiving_yards = models.FloatField(default=0)
    receiving_tds = models.IntegerField(default=0)
    carrys = models.IntegerField(default=0)
    rush_yards = models.IntegerField(default=0)
    avg_rush_yards_perCarry = models.FloatField(default=0)
    rush_tds = models.IntegerField(default=0)
    fumbles = models.IntegerField(default=0)
    kick_1_19 = models.IntegerField(default=0)
    kick_20_29 = models.IntegerField(default=0)
    kick_30_39 = models.IntegerField(default=0)
    kick_40_49 = models.IntegerField(default=0)
    kick_50 = models.IntegerField(default=0)
    fg_perc = models.FloatField(default=0)
    fg_attempts = models.IntegerField(default=0)
    fg_made = models.IntegerField(default=0)
    extra_points_made = models.IntegerField(default=0)
    extra_points_attempts = models.IntegerField(default=0)
    total_fantasy_points = models.FloatField(default=0)

    def __str__(self):
        return f"{self.firstName} {self.lastName} game stats"

class Game(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    season_type = models.CharField(max_length=100, default='0')
    date = models.CharField(max_length=100, default='0')
    home_team = models.CharField(max_length=100, default='0')
    away_team = models.CharField(max_length=100, default='0')
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    current_play = models.CharField(max_length=200, default='0')
    week = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.id} {self.home_team} vs {self.away_team} {self.date} {self.current_play}"


class League(models.Model):
    id = models.AutoField(primary_key=True)  # Unique identifier for the league
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='owned_leagues')
    players = models.ManyToManyField(Player, related_name='leagues', blank=True)  # Players that belong to the league
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"League: {self.name}, Owner: {self.owner.firstName} {self.owner.lastName}"

class Team(models.Model):
    id = models.AutoField(primary_key=True)  # Unique identifier for the team
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(Player, related_name='teams_owned', on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    players = models.ManyToManyField(Player, related_name='teams')
    nfl_players = models.ManyToManyField('Player', related_name='nfl_teams', blank=True)  # Link to NFL players by their IDs
    
    def __str__(self):
        return f"Team: {self.name}, Owner: {self.owner.firstName} {self.owner.lastName}"

class LeagueSettings(models.Model):
    league = models.OneToOneField(League, on_delete=models.CASCADE)
    max_players = models.IntegerField(default=12)  # Max number of players
    scoring_system = models.CharField(max_length=100, default='Standard')  # Example scoring system

    def __str__(self):
        return f"Settings for {self.league.name}"