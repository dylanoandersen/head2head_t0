from django.shortcuts import render
from django.http import JsonResponse
from .models import Player, Player_News, Player_Stats
from .serializers import PlayerInfoSerializer, PlayerStatSerializer, PlayerNewsSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.viewsets import ModelViewSet
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q




import json

# Create your views here.

@api_view(['GET'])
def allPlayer(request):
    player = Player.objects.all()
    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player, many=True)
        return Response({"Player": serializer.data})
    else:
        print('Could not grab all players')

# @api_view(['GET'])
# def player_info(request,id):
#     try:
#         player = Player.objects.get(pk=id)
#     except Player.DoesNotExist:
#         return Response(status=status.HTTP_404_NOT_FOUND)

#     if request.method == 'GET':
#         serializer = PlayerInfoSerializer(player)
#         return Response({"Player": serializer.data})

@api_view(['GET'])
def player_info(request, id):
    try:
        # Prefetch related player stats for this player
        player = Player.objects.prefetch_related('player_stats_set').get(pk=id)
    except Player.DoesNotExist:
        return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)

    # Prepare the player data to be returned
    player_data = {
        "id": player.id,
        "firstName": player.firstName,
        "lastName": player.lastName,
        "team": player.team,  # Assuming team has a name field
        "position": player.position,
        "jersey": player.jersey,
        "age": player.age,
        "weight": player.weight,
        "displayHeight": player.displayHeight,
        "player_stats": [],
    }

@api_view(['GET'])
def player_stats(request,id):
    try:
        player_stats = Player_Stats.objects.filter(player=id)
    except Player.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerStatSerializer(player_stats, many=True)
        return Response({"Player_stats": serializer.data})

@api_view(['GET'])
def player_news(request,id):
    try:
        player_news = Player_News.objects.filter(player=id)
    except Player.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerNewsSerializer(player_news, many=True)
        return Response({"Player_news": serializer.data})


@api_view(['POST'])
def topTenPlayers(request):
    if request.method == 'POST':
        players = Player.objects.all().order_by('-yearly_proj')[:10]
        serializer = PlayerInfoSerializer(players, many=True)
        return Response({"TopTen": serializer.data})
    return Response(status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def search_player(request):
    if request.method == "GET":
        name_query = request.GET.get("name", "").strip()

        if not name_query:
            return JsonResponse({"error": "No name provided"}, status=400)

        # Split the query into first and last name parts
        name_parts = name_query.split()

        if len(name_parts) == 1:
            # Search for first name or last name if only one part is provided
            players = Player.objects.filter(
                Q(firstName__icontains=name_parts[0]) | Q(lastName__icontains=name_parts[0])
            )
        elif len(name_parts) == 2:
            # If both first and last names are provided, search both fields
            players = Player.objects.filter(
                Q(firstName__icontains=name_parts[0]) & Q(lastName__icontains=name_parts[1])
            )
        else:
            # If the query contains more than 2 parts, return an error
            return JsonResponse({"error": "Invalid name format. Please provide only a first and last name."}, status=400)

        if not players.exists():
            return JsonResponse({"players": []})

        player_data = [
            {
                "id": player.id,
                "firstName": player.firstName,
                "lastName": player.lastName,
                "team": player.team,
                "position": player.position,
                "jersey": player.jersey,
                "headshot": player.headshot,
                "age": player.age,  # Add the age
                "weight": player.weight,  # Add the weight
                "height": player.displayHeight,  # Add the height
            }
            for player in players
        ]

        return JsonResponse({"players": player_data})
    
    return JsonResponse({"error": "Invalid request method"}, status=405)


