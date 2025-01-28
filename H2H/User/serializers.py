from django.contrib.auth.models import User
from rest_framework import serializers
from .models import traditional_redraft

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}
        
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# add more later
class ReDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = traditional_redraft
        fields = ['id', 'title', 'author', 'QB', 'RB1', 'RB2', 'WR1', ]