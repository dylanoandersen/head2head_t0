from rest_framework import serializers
from .models import Player
from .models import League

class PlayerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'firstName', 'lastName', 'team', 'position', 'jersey', 'age', 'weight', 'displayHeight']
        

class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = ['id', 'name', 'owner', 'players', 'created_at']
