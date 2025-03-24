from django.shortcuts import render
from django.http import JsonResponse
from .models import Player, Player_News, Player_Stats
from .serializers import PlayerInfoSerializer, PlayerStatSerializer, PlayerNewsSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator  # For pagination


@api_view(['GET'])
def allPlayer(request):
    player = Player.objects.all()
    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player, many=True)
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

# @api_view(['GET'])
# def player_info(request, id):
#     try:
#         # Prefetch related player stats for this player
#         player = Player.objects.prefetch_related('player_stats_set').get(pk=id)
#     except Player.DoesNotExist:
#         return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)

#     # Prepare the player data to be returned
#     player_data = {
#         "id": player.id,
#         "firstName": player.firstName,
#         "lastName": player.lastName,
#         "team": player.team,  # Assuming team has a name field
#         "position": player.position,
#         "jersey": player.jersey,
#         "age": player.age,
#         "weight": player.weight,
#         "displayHeight": player.displayHeight,
#         "player_stats": [],
#     }

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
    search_query = request.data.get("name", "").strip()  # Get search term from request data

    if search_query:
        # Split search query into words
        name_parts = search_query.split()
        
        if len(name_parts) == 2:
            # If two words (assume first and last name)
            first_name, last_name = name_parts
            players = Player.objects.filter(
                Q(firstName__icontains=first_name) & Q(lastName__icontains=last_name)
            ).order_by('-yearly_proj')[:10]
        else:
            # If single word, search both first and last name fields
            players = Player.objects.filter(
                Q(firstName__icontains=search_query) | Q(lastName__icontains=search_query)
            ).order_by('-yearly_proj')[:10]
    else:
        # If no search term, return top 10 yearly projected players
        players = Player.objects.all().order_by('-yearly_proj')[:10]

    serializer = PlayerInfoSerializer(players, many=True)
    return Response({"TopTen": serializer.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_player(request):
    search_query = request.GET.get("name", "").strip()  # Get search term
    page = int(request.GET.get("page", 1))  # Get current page
    players_per_page = 10 # Players per page

    if search_query:
        # Split search query into words
        name_parts = search_query.split()
        
        if len(name_parts) == 2:
            # If two words (assume first and last name)
            first_name, last_name = name_parts
            players = Player.objects.filter(
                Q(firstName__icontains=first_name) & Q(lastName__icontains=last_name)
            )
        else:
            # If single word, search both first and last name fields
            players = Player.objects.filter(
                Q(firstName__icontains=search_query) | Q(lastName__icontains=search_query)
            )
    else:
        # If no search term, return all players paginated
        players = Player.objects.all()

    paginator = Paginator(players, players_per_page)
    paginated_players = paginator.get_page(page)

    return Response({
        "Player": PlayerInfoSerializer(paginated_players, many=True).data,
        "totalPages": paginator.num_pages
    })
