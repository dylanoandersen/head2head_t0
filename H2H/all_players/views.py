from django.shortcuts import render
from django.http import JsonResponse
from .models import Player, League, Team
from .serializers import PlayerInfoSerializer, LeagueSerializer, TeamSerializer
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

    # Loop through player stats
    for stat in player.player_stats_set.all():
        # Initialize a dictionary for stats based on position
        stats = {}

        if player.position in ['Running Back', 'Wide Receiver', 'Tight End']:  # Running Backs, Wide Receivers, Tight Ends
            stats = {
                'carries': stat.carrys,
                'rushing_yards': stat.rush_yards,
                'rushing_tds': stat.rush_tds,
                'receptions': stat.catches,
                'receiving_yards': stat.receiving_yards,
                'receiving_tds': stat.receiving_tds,
                'targets': stat.targets,
                'fantasy_points': stat.total_fantasy_points,
                'projected_fantasy_points':  stat.proj_fantasy,
                'avg_yards_per_carry': stat.avg_rush_yards_perCarry,
                'avg_yards_per_reception': stat.avg_recieving_yards_perCatch
            }

        elif player.position == 'Place kicker':  # Kicker
            stats = {
                'field_goals_made': stat.fg_made,
                'field_goals_attempted': stat.fg_attempts,
                'field_goal_percentage': stat.fg_perc,
                'extra_points': stat.extra_points_made,
                'fantasy_points': stat.total_fantasy_points,
                'projected_fantasy_points': stat.proj_fantasy
            }

        elif player.position == 'Quarterback':  # Quarterback
            stats = {
                'completions': stat.completions,
                'passing_yards': stat.pass_yards,
                'passing_tds': stat.pass_tds,
                'interceptions': stat.ints,
                'fumbles': stat.fumbles,
                'fantasy_points': stat.total_fantasy_points,
                'projected_fantasy_points':  stat.proj_fantasy,
                'completion_percentage': stat.completions_perc
            }

        # Add the stats for this week to the player_data
        stats['week'] = stat.week
        player_data["player_stats"].append(stats)

    return Response({"Player": player_data})

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
                "age": player.age,  # Add the age
                "weight": player.weight,  # Add the weight
                "height": player.displayHeight,  # Add the height
            }
            for player in players
        ]

        return JsonResponse({"players": player_data})
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

@api_view(['POST'])
def create_league(request):
    if request.method == 'POST':
        # Pass the request data to the serializer
        serializer = LeagueSerializer(data=request.data, context={'request': request})

        # Validate and save the league if the data is valid
        if serializer.is_valid():
            league = serializer.save()  # The owner is set automatically
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LeagueListCreateView(generics.ListCreateAPIView):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class LeagueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    permission_classes = [permissions.IsAuthenticated]

class TeamListCreateView(generics.ListCreateAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

class TeamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
