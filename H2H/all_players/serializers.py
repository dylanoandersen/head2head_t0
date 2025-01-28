from rest_framework import serializers
from .models import Player


class PlayerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'firstName', 'lastName', 'team', 'position', 'jersey']
