from django.contrib.auth import authenticate
from django.shortcuts import render
from datetime import datetime;
from .models import Profile, League, Team, Draft
from all_players.models import Player, Player_Stats# Import the Player model from the all_players app
from django.contrib.auth.models import User

from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, permissions
import logging

from .serializers import UserSerializer, ProfileSerializer, LeagueSerializer, TeamSerializer, PlayerSerializer
import random

logger = logging.getLogger(__name__)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_league_settings(request, league_id):
    logger.info("Received request to update league settings for league_id: %s", league_id)
    logger.info("Request data: %s", request.data)

    try:
        league = League.objects.get(id=league_id, owner=request.user)
    except League.DoesNotExist:
        logger.error("League not found or user is not the owner.")
        return Response({'error': 'League not found or you are not the owner.'}, status=403)

    data = request.data

    # Validate draft_date
    if 'draft_date' in data:
        draft_date = data['draft_date']
        try:
            parsed_date = datetime.strptime(draft_date, "%Y-%m-%dT%H:%M:%S")
            if parsed_date < datetime.now():
                logger.error("Draft date must be in the future. Received: %s", draft_date)
                return Response({'error': 'Draft date must be in the future.'}, status=400)
        except ValueError as e:
            logger.error("Invalid draft_date format: %s", draft_date)
            return Response({'error': 'Invalid draft date format. Use ISO 8601 format.'}, status=400)

    # Validate join_code uniqueness
    if 'join_code' in data and League.objects.filter(join_code=data['join_code']).exclude(id=league_id).exists():
        logger.error("Join code already exists: %s", data['join_code'])
        return Response({'error': 'Join code already exists.'}, status=400)

    # Update fields
    for field in ['draft_date', 'time_per_pick', 'positional_betting', 'max_capacity', 'private', 'join_code']:
        if field in data:
            logger.info("Updating field %s to %s", field, data[field])
            setattr(league, field, data[field])

    try:
        league.save()
        logger.info("League settings updated successfully for league_id: %s", league_id)
        return Response({'success': 'League settings updated successfully.'})
    except Exception as e:
        logger.error("Error saving league settings: %s", str(e))
        return Response({'error': 'Failed to update league settings.'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_pick(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        draft = Draft.objects.get(league=league)
    except (League.DoesNotExist, Draft.DoesNotExist):
        return Response({'error': 'League or draft not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    player_id = request.data.get('player_id')

    if user.id != draft.get_next_pick():
        return Response({'error': 'It is not your turn to pick'}, status=status.HTTP_403_FORBIDDEN)

    try:
        player = Player.objects.get(id=player_id)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)

    draft.picks.append({'user_id': user.id, 'player_id': player.id})
    draft.current_pick += 1
    draft.save()

    return Response({'success': 'Pick made successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_draft(request, league_id):
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response({'error': 'League not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user != league.owner:
        return Response({'error': 'You are not the owner of this league'}, status=status.HTTP_403_FORBIDDEN)

    if league.draftStarted:
        return Response({'error': 'Draft has already started'}, status=status.HTTP_400_BAD_REQUEST)

    # Randomize the draft order
    users = list(league.users.all())
    if not users:
        return Response({'error': 'No users in the league to start the draft'}, status=status.HTTP_400_BAD_REQUEST)

    random.shuffle(users)
    draft_order = [user.id for user in users]

    # Create or update the draft
    draft, created = Draft.objects.get_or_create(league=league, defaults={
        'draft_order': draft_order,
        'current_pick': 0,
        'picks': []
    })

    if not created:
        draft.draft_order = draft_order
        draft.current_pick = 0
        draft.picks = []
        draft.save()

    league.draftStarted = True
    league.save()

    # Assign the draft URL
    draft_url = f"/draft/{league_id}/"
    logger.info(f"Draft started successfully. Draft URL: {draft_url}")
    return Response({'success': 'Draft started successfully', 'draft_url': draft_url}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_draft_status(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        draft = Draft.objects.get(league=league)
    except (League.DoesNotExist, Draft.DoesNotExist):
        return Response({'error': 'League or draft not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user not in league.users.all() and request.user != league.owner:
        return Response({'error': 'You are not a member of this league'}, status=status.HTTP_403_FORBIDDEN)

    current_pick_user = draft.get_next_pick()
    return Response({'draftStarted': league.draftStarted, 'currentPickUser': current_pick_user}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_league_membership(request, league_id):
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response({'error': 'League not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user not in league.users.all() and request.user != league.owner:
        return Response({'error': 'You are not a member of this league'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'success': 'User is a member of the league'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_current_pick_user(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        draft = Draft.objects.get(league=league)
    except (League.DoesNotExist, Draft.DoesNotExist):
        return Response({'error': 'League or draft not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get the current pick user from the draft
    current_pick_user = draft.get_next_pick()

    # Check if the logged-in user matches the current pick user
    is_current_pick_user = request.user.id == current_pick_user

    return Response({
        'isCurrentPickUser': is_current_pick_user,
        'currentPickUser': current_pick_user,
        'loggedInUserId': request.user.id
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_draft_picks(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        draft = Draft.objects.get(league=league)
    except (League.DoesNotExist, Draft.DoesNotExist):
        return Response({'error': 'League or draft not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'picks': draft.picks}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    logger.info("Received data: %s", request.data)
    user_serializer = UserSerializer(data=request.data)
    if user_serializer.is_valid():
        user = user_serializer.save()
        profile_data = {
            'date_of_birth': request.data.get('dob'),
            'profile_picture': request.FILES.get('profilePicture')
        }
        logger.info("Profile data: %s", profile_data)
        Profile.objects.update_or_create(user=user, defaults=profile_data)
        return Response({'success': 'User registered successfully'}, status=status.HTTP_201_CREATED)
    else:
        logger.error("User validation errors: %s", user_serializer.errors)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_by_id(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        print("username is",user.username)
        return Response({'username': user.username}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    user_serializer = UserSerializer(user)
    profile_serializer = ProfileSerializer(user.profile)
    return Response({
        'user': user_serializer.data,
        'profile': profile_serializer.data
    })



@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_info(request):
    user = request.user
    user_serializer = UserSerializer(user, data=request.data, partial=True)
    if user_serializer.is_valid():
        user_serializer.save()
        profile_data = request.data.get('profile', {})
        if profile_data:
            profile_serializer = ProfileSerializer(user.profile, data=profile_data, partial=True)
            if profile_serializer.is_valid():
                profile_serializer.save()
        return Response({'success': 'User information updated successfully'})
    else:
        logger.error("User validation errors: %s", user_serializer.errors)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user_profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            token = AccessToken(request.headers.get('Authorization').split()[1])
            user = request.user
            return Response({'username': user.username}, status=200)
        except (InvalidToken, TokenError) as e:
            return Response({'error': str(e)}, status=401)
        
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def myPlayers(request):
    objectList = []
    pointList = []
    player_parms = request.GET.get('players', None)
    player_list = player_parms.split(',') if player_parms else []
    print(f"Player List: {player_list}")  # Log the player list
    for id in player_list:
        if id == "N/A":
        # Create a placeholder "empty" player object (not saved to the DB)
            empty_player = Player(
                id=None,
                firstName="Empty",
                lastName="",
                status="x",
                position="",
                team="",
            )
            setattr(empty_player, 'proj_fantasy', None)
            setattr(empty_player, 'total_fantasy_points', None)
            objectList.append(empty_player)
            continue
        currentP = Player.objects.get(id=id)
        try:
            latest = Player_Stats.objects.get(player=currentP, week=1)
            setattr(currentP, 'proj_fantasy', latest.proj_fantasy)  # Attach to Player object
            setattr(currentP, 'total_fantasy_points', latest.total_fantasy_points)  # Attach to Player object
        except:
            setattr(currentP, 'proj_fantasy', None)  # Set default if no stats
            setattr(currentP, 'total_fantasy_points', None)

        objectList.append(currentP)

    serializer = PlayerSerializer(objectList, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def userTeam(request, LID):
    UID = request.user.id
    if request.method == 'GET':
        try:
            league = League.objects.get(id=LID)
            user = User.objects.get(id=UID)
            team = Team.objects.get(league=league, author=user)
        except (League.DoesNotExist, User.DoesNotExist, Team.DoesNotExist):
            return Response({"error": "Team not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({"error": "Invalid request method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    serializer = TeamSerializer(team)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_leagues(request):
    leagues = request.user.joined_leagues.all() | request.user.owned_leagues.all()
    serializer = LeagueSerializer(leagues, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_private_league(request):
    print("join_private_league endpoint hit")
    join_code = request.data.get("join_code", "").strip()
    print(f"Join code received: {join_code}")

    try:
        league = League.objects.get(join_code=join_code)
    except League.DoesNotExist:
        return Response({"error": "Invalid join code"}, status=status.HTTP_404_NOT_FOUND)

    if league.users.count() >= league.max_capacity:
        return Response({"error": "This league is full."}, status=status.HTTP_400_BAD_REQUEST)

    league.users.add(request.user)
    return Response({"message": "Successfully joined the league!"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_public_league(request, league_id):
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response({"error": "League not found"}, status=status.HTTP_404_NOT_FOUND)

    if league.private:
        return Response({"error": "This league is private. Use a join code."}, status=status.HTTP_403_FORBIDDEN)

    if league.users.count() >= league.max_capacity:
        return Response({"error": "This league is full."}, status=status.HTTP_400_BAD_REQUEST)

    league.users.add(request.user)
    return Response({"message": "Successfully joined the league!"}, status=status.HTTP_200_OK)



def search_league(request):
    if request.method == "GET":
        name_query = request.GET.get("name", "").strip()
        print(f"Search Term: {name_query}")  # Log the search term

        if not name_query:
            return JsonResponse({"error": "No name provided"}, status=400)

        # Ensure filtering works correctly
        leagues = League.objects.filter(name__icontains=name_query)
        print(f"Leagues Found: {list(leagues.values('id', 'name'))}")  # Log the filtered leagues

        if not leagues.exists():
            return JsonResponse({"results": []})

        league_data = [
            {
                "id": league.id,
                "name": league.name,
                "owner": league.owner.username,
                "draft_date": league.draft_date,
            }
            for league in leagues
        ]

        return JsonResponse({"results": league_data})

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_league(request):
    join_code = request.data.get("join_code", "").strip()
    if join_code and League.objects.filter(join_code=join_code).exists():
        return Response({"error": "Join code already exists"}, status=status.HTTP_400_BAD_REQUEST)

    serializer = LeagueSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        league = serializer.save()

        league.users.add(request.user)


        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_join_code(request, join_code):
    exists = League.objects.filter(join_code=join_code).exists()
    return Response({"exists": exists}, status=status.HTTP_200_OK)


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