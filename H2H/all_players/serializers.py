from rest_framework import serializers
from .models import Player, Player_Stats, Player_News

class PlayerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'firstName', 'headshot', 'lastName', 'team', 'position', 'jersey', 'age', 'weight', 'displayHeight']

class PlayerStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player_Stats
        fields = ['id','player','game','total_fantasy_points','proj_fantasy','week','pass_att','completions','pass_yards','pass_tds','ints','sacks','targets','catches','receiving_yards','avg_receiving_yards_perCatch','receiving_tds','carrys','avg_rush_yards_perCarry','rush_yards','rush_tds','fumbles','return_td','two_pt_made','kick_1_19','kick_20_29','kick_30_39','kick_40_49','kick_50','fg_made','fg_attempts','fg_perc','extra_points_made','extra_points_attempts']

class PlayerNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player_News
        fields = ['id','player','headline','text','date']