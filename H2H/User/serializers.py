from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Profile, League, Team
from all_players.models import Player

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        return user
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'profile_picture']

class PlayerSerializer(serializers.ModelSerializer):
    proj_fantasy = serializers.SerializerMethodField()
    total_fantasy_points = serializers.SerializerMethodField()
    pass_yards = serializers.SerializerMethodField()
    pass_tds = serializers.SerializerMethodField()
    receiving_yards = serializers.SerializerMethodField()
    receiving_tds = serializers.SerializerMethodField()
    rush_yards = serializers.SerializerMethodField()
    rush_tds = serializers.SerializerMethodField()
    extra_points_made = serializers.SerializerMethodField()
    fg_made = serializers.SerializerMethodField()
    class Meta:
        model = Player
        fields = ['id', 'firstName', 'lastName', 'status', 'position', 'team', 'proj_fantasy', 'total_fantasy_points', 
                  'pass_yards', 'pass_tds', 'receiving_yards', 'receiving_tds', 'rush_yards', 'rush_tds', 'fg_made', 'extra_points_made']

    def get_proj_fantasy(self, obj):
        return getattr(obj, 'proj_fantasy', None)  # Get dynamically attached field
    def get_total_fantasy_points(self, obj):
        return getattr(obj, 'total_fantasy_points', None)  # Get dynamically attached field
    def get_pass_yards(self, obj):
        return getattr(obj, 'pass_yards', None)
    def get_pass_tds(self, obj):
        return getattr(obj, 'pass_tds', None)
    def get_receiving_yards(self, obj):
        return getattr(obj, 'receiving_yards', None)
    def get_receiving_tds(self, obj):
        return getattr(obj, 'receiving_tds', None)
    def get_rush_yards(self, obj):
        return getattr(obj, 'rush_yards', None)
    def get_rush_tds(self, obj):
        return getattr(obj, 'rush_tds', None)
    def get_fg_made(self, obj):
        return getattr(obj, 'fg_made', None)
    def get_extra_points_made(self, obj):
        return getattr(obj, 'extra_points_made', None)


class LeagueSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)  # Nested owner info
    teams = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), many=True, required=False)
    users = UserSerializer(many=True, read_only=True)  # Nested users info

    class Meta:
        model = League
        fields = ['id', 'name', 'owner', 'draft_date', 'time_per_pick', 'positional_betting',
                  'max_capacity', 'private', 'join_code', 'users', 'teams', 'draftStarted', 'draftComplete']

    def create(self, validated_data):
        request = self.context.get('request', None)
        if request and request.user:
            validated_data['owner'] = request.user  # Set the owner to the logged-in user

        league = League.objects.create(**validated_data)
        return league
class TeamSerializer(serializers.ModelSerializer):
    league = LeagueSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    class Meta:
        model = Team
        fields = ['id', 'title', 'QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLX', 'K', 'DEF', 
                  'BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2', 'author', 'league', 'rank']

