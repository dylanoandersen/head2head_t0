from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Profile, League, Team, Matchup, Notification, Bet
from all_players.models import Player



class BetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bet
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'link', 'is_read', 'created_at']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'profile_picture', 'currency']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)  # Add the profile field
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name', 'profile']
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
        return getattr(obj, 'proj_fantasy', None)
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
                  'BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2', 'author', 'league', 'rank', 'wins', 'losses', 'points_for', 'points_against']

class MatchupSerializer(serializers.ModelSerializer):
    team1 = UserSerializer(read_only=True)
    team2 = UserSerializer(read_only=True)

    class Meta:
        model = Matchup
        fields = ['id','team1','team2','team1score', 'team2score']

class PlayerSlotSerializer(serializers.Serializer):
    id = serializers.CharField()
    fullName = serializers.CharField()
    proj_fantasy = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    total_fantasy_points = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)

class CustomTeamSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    rank = serializers.IntegerField()
    author = serializers.CharField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    points_for = serializers.IntegerField()
    points_against = serializers.IntegerField()
    QB = PlayerSlotSerializer(allow_null=True)
    RB1 = PlayerSlotSerializer(allow_null=True)
    RB2 = PlayerSlotSerializer(allow_null=True)
    WR1 = PlayerSlotSerializer(allow_null=True)
    WR2 = PlayerSlotSerializer(allow_null=True)
    TE = PlayerSlotSerializer(allow_null=True)
    FLX = PlayerSlotSerializer(allow_null=True)
    K = PlayerSlotSerializer(allow_null=True)
    DEF = PlayerSlotSerializer(allow_null=True)
    BN1 = PlayerSlotSerializer(allow_null=True)
    BN2 = PlayerSlotSerializer(allow_null=True)
    BN3 = PlayerSlotSerializer(allow_null=True)
    BN4 = PlayerSlotSerializer(allow_null=True)
    BN5 = PlayerSlotSerializer(allow_null=True)
    BN6 = PlayerSlotSerializer(allow_null=True)
    IR1 = PlayerSlotSerializer(allow_null=True)
    IR2 = PlayerSlotSerializer(allow_null=True)
