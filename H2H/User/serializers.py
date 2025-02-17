from django.contrib.auth.models import User
from rest_framework import serializers
from .models import traditional_redraft, Profile


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
        model = traditional_redraft
        fields = ['id', 'title', 'author', 'QB', 'RB1', 'RB2', 'WR1', ]

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'profile_picture']