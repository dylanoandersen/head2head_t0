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
        return f"{self.id}{self.firstName} {self.lastName}"

class Player_Stats(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    game_id = models.CharField(max_length=20, default='0')
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
    avg_recieving_yards_perGame = models.IntegerField(default=0)
    avg_recieving_yards_perCatch = models.FloatField(default=0)
    receiving_yards = models.FloatField(default=0)
    receiving_tds = models.IntegerField(default=0)
    carrys = models.IntegerField(default=0)
    rush_yards = models.IntegerField(default=0)
    avg_rush_yards_perGame = models.FloatField(default=0)
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
    total_fantasy_points = models.FloatField(default=0)

class Game(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    season_type = models.CharField(max_length=100, default='0')
    date = models.CharField(max_length=100, default='0')
    home_team = models.CharField(max_length=100, default='0')
    away_team = models.CharField(max_length=100, default='0')
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    current_play = models.CharField(max_length=200, default='0')

    def __str__(self):
        return f"{self.id}{self.home_team} vs {self.away_team} {self.date} {self.current_play}"
