from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Profile, League, Team


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

# add more later
class ReDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'title', 'author', 'QB', 'RB1', 'RB2', 'WR1', ]

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'profile_picture']



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
    class Meta:
        model = Team
        fields = '__all__'