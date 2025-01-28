from django.shortcuts import render
from django.http import JsonResponse
from .models import Player
from .serializers import PlayerInfoSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

# Create your views here.

@api_view(['GET'])
def allPlayer(request):
    player = Player.objects.all()
    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player)
        return Response({"Player": serializer.data})
    else:
        print('Could not grab all players')

@api_view(['GET'])
def player_info(request,id):
    try:
        player = Player.objects.get(pk=id)
    except Player.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player)
        return Response({"Player": serializer.data})


