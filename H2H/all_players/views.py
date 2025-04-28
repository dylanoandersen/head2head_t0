from django.shortcuts import render
from django.http import JsonResponse
from .models import Player, Player_News, Player_Stats
from User.models import Week
from .serializers import PlayerInfoSerializer, PlayerStatSerializer, PlayerNewsSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator

@api_view(['GET'])
def batch_player_info(request):
    """
    Fetch multiple players by their IDs.
    """
    try:
        ids = request.query_params.getlist('ids[]') 
        if not ids:
            return Response({"error": "No player IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        players = Player.objects.filter(pk__in=ids)
        if not players.exists():
            return Response({"error": "No players found for the provided IDs."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PlayerInfoSerializer(players, many=True)
        return Response({"Players": serializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def week(request):
    current_week = Week.objects.get(id=1).week
    return Response({"week": current_week})

@api_view(['GET'])
def allPlayer(request):
    player = Player.objects.all()
    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player, many=True)
        return Response({"Player": serializer.data})
    else:
        print('Could not grab all players')

@api_view(['GET'])
def player_info(request, id=None):
    """
    Handles both individual and batch player information retrieval.
    - If `id` is provided in the URL, retrieves a single player.
    - If `ids` query parameter is provided, retrieves a batch of players.
    """
    try:
        ids = request.query_params.getlist('ids') 
        if ids:
            players = Player.objects.filter(pk__in=ids)
            if not players.exists():
                return Response({"error": "No players found for the provided IDs."}, status=status.HTTP_404_NOT_FOUND)
            serializer = PlayerInfoSerializer(players, many=True)
            return Response({"Players": serializer.data})

        if id is not None:
            player = Player.objects.get(pk=id)
            serializer = PlayerInfoSerializer(player)
            return Response({"Player": serializer.data})

        return Response({"error": "No player ID or batch IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

    except Player.DoesNotExist:
        return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)

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
        if id == 99:
            player_news = Player_News.objects.all()
        else:
            player_news = Player_News.objects.filter(player=id)
    except Player.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerNewsSerializer(player_news, many=True)
        return Response({"Player_news": serializer.data})


@api_view(['POST'])
def topTenPlayers(request):
    search_query = request.data.get("name", "").strip()

    if search_query:
        name_parts = search_query.split()
        
        if len(name_parts) == 2:
            first_name, last_name = name_parts
            players = Player.objects.filter(
                Q(firstName__icontains=first_name) & Q(lastName__icontains=last_name)
            ).order_by('-yearly_proj')[:10]
        else:
            players = Player.objects.filter(
                Q(firstName__icontains=search_query) | Q(lastName__icontains=search_query)
            ).order_by('-yearly_proj')[:10]
    else:
        players = Player.objects.all().order_by('-yearly_proj')[:10]

    serializer = PlayerInfoSerializer(players, many=True)
    return Response({"TopTen": serializer.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_player(request):
    search_query = request.GET.get("name", "").strip()
    team_query = request.GET.get("team", "").strip()
    position_query = request.GET.get("position", "").strip()
    status_query = request.GET.get("status", "").strip()
    page = int(request.GET.get("page", 1))
    players_per_page = 10

    players = Player.objects.all()

    if search_query:
        name_parts = search_query.split()
        if len(name_parts) == 2:
            first_name, last_name = name_parts
            players = players.filter(
                Q(firstName__icontains=first_name) & Q(lastName__icontains=last_name)
            )
        else:
            players = players.filter(
                Q(firstName__icontains=search_query) | Q(lastName__icontains=search_query)
            )
    if team_query:
        players = players.filter(team__icontains=team_query)
    if position_query:
        players = players.filter(position__icontains=position_query)
    if status_query:
        players = players.filter(status__icontains=status_query)

    players = players.order_by("-yearly_proj")

    paginator = Paginator(players, players_per_page)
    paginated_players = paginator.get_page(page)

    return Response({
        "Player": PlayerInfoSerializer(paginated_players, many=True).data,
        "totalPages": paginator.num_pages
    })