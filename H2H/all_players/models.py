from django.db import models

class Player(models.Model):
    id = models.CharField(max_length=50, primary_key=True) 
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
    yearly_proj = models.FloatField(default=0)
    headshot = models.ImageField(upload_to='images/headShots/', blank=True, null=True)

    def __str__(self):
        return f"{self.id} {self.firstName} {self.lastName}"
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
class Player_Stats(models.Model):
    id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_column='player_id')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, db_column='game_id')
    firstName = models.CharField(max_length=20, default='0')
    lastName = models.CharField(max_length=20, default='0')
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
    avg_receiving_yards_perCatch = models.FloatField(default=0)
    receiving_yards = models.FloatField(default=0)
    receiving_tds = models.IntegerField(default=0)
    carrys = models.IntegerField(default=0)
    rush_yards = models.IntegerField(default=0)
    avg_rush_yards_perCarry = models.FloatField(default=0)
    rush_tds = models.IntegerField(default=0)
    fumbles = models.IntegerField(default=0)
    return_td = models.IntegerField(default=0)
    two_pt_made = models.IntegerField(default=0)
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
    proj_fantasy = models.DecimalField(default=0, max_digits=5, decimal_places=2)
    total_fantasy_points = models.DecimalField(default=0, max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.firstName} {self.lastName} game stats"

class Player_News(models.Model):
    id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_column='player_id')
    headline = models.CharField(max_length=200, default='0')
    text = models.TextField(default='0')
    date = models.CharField(max_length=100, default='0')

    def __str__(self):
        return f"{self.player} news"

class Def_Stats(models.Model):
    id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_column='player_id')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, db_column='game_id')
    location = models.CharField(max_length=20, default='0')
    team = models.CharField(max_length=20, default='0')
    week = models.IntegerField(default=0)
    pts_allowed = models.IntegerField(default=0)
    inter = models.IntegerField(default=0)
    sacks = models.IntegerField(default=0)
    safties = models.IntegerField(default=0)
    touchdowns = models.IntegerField(default=0)
    forc_fum = models.IntegerField(default=0)
    fumble_rec = models.IntegerField(default=0)
    proj_fantasy = models.DecimalField(default=0, max_digits=5, decimal_places=2)
    total_fantasy_points = models.DecimalField(default=0, max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.team} game stats"