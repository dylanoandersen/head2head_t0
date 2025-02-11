from django.shortcuts import render, redirect,  get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Player
from .serializers import PlayerInfoSerializer, LeagueSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.viewsets import ModelViewSet
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import League
from .forms import LeagueForm
from django.contrib.auth.models import User

import json

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


@csrf_exempt
def create_league(request):
    if request.method == 'POST':
        data = json.loads(request.body)  # If you're sending JSON, parse it
        form = LeagueForm(data)
        if form.is_valid():
            # Save the league instance
            league = form.save(commit=False)
            # Ensure the owner is the logged-in user (if logged in)
            if request.user.is_authenticated:
                league.owner = request.user.player  # Assuming Player is linked with the user model
            league.save()
            
            # Return a successful response
            return JsonResponse({'message': 'League created successfully', 'league_id': league.id}, status=201)
        return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def view_league(request, league_id):
    league = get_object_or_404(League, id=league_id)
    return render(request, 'view_league.html', {'league': league})

def add_player_to_league(request, league_id):
    league = get_object_or_404(League, id=league_id)
    if request.method == 'POST':
        player_id = request.POST.get('player_id')  # Assume player ID is passed in POST
        player = get_object_or_404(Player, id=player_id)
        league.players.add(player)  # Add player to the league
        return redirect('view_league', league_id=league.id)
    return HttpResponse(status=400)  # Invalid request

@api_view(['POST'])
def create_league_api(request):
    if request.method == 'POST':
        serializer = LeagueSerializer(data=request.data)
        if serializer.is_valid():
            # Look up the user by username
            user = User.objects.get(username=request.data['owner'])
            serializer.validated_data['owner'] = user  # Assign the actual user object

            league = serializer.save()
            return Response({
                'id': league.id,
                'name': league.name,
                'owner': league.owner.id,  # Return the owner's id
                'settings': league.settings,
            }, status=201)  # League created successfully
        return Response(serializer.errors, status=400)  # Return errors if invalid

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