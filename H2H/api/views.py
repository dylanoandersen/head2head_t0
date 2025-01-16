from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from all_players.models import Player

@api_view(['GET'])
def getData(request):
    return Response(Player.objects.all().values())
