from rest_framework import serializers
from .models import Player, Player_Stats, League, Team
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError



class PlayerStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player_Stats
        fields = [
            'week', 'pass_att', 'completions', 'completions_perc', 'pass_yards',
            'avg_pass_yards_completions', 'pass_tds', 'ints', 'sacks', 'catches',
            'targets', 'avg_recieving_yards_perCatch', 'receiving_yards', 
            'receiving_tds', 'carrys', 'rush_yards', 'avg_rush_yards_perCarry',
            'rush_tds', 'fumbles', 'return_td', 'two_pt_made', 'kick_1_19', 
            'kick_20_29', 'kick_30_39', 'kick_40_49', 'kick_50', 'fg_perc', 
            'fg_attempts', 'fg_made', 'extra_points_made', 'extra_points_attempts', 
            'proj_fantasy', 'total_fantasy_points'
        ]


class PlayerInfoSerializer(serializers.ModelSerializer):
    player_stats = PlayerStatsSerializer(many=True, read_only=True, source='player_stats_set')

    class Meta:
        model = Player
        fields = [
            'id', 'firstName', 'lastName', 'team', 'position', 'jersey',
            'age', 'weight', 'displayHeight', 'player_stats'
        ]

class LeagueSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    teams = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), many=True, required=False)

    class Meta:
        model = League
        fields = ['id', 'name', 'owner', 'draft_date', 'time_per_pick', 'positional_betting', 'teams']

    def create(self, validated_data):
        # If owner is not provided, set it to the currently logged-in user
        if 'owner' not in validated_data:
            validated_data['owner'] = self.context['request'].user

        # Create the League instance
        league = League.objects.create(**validated_data)

        return league

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
