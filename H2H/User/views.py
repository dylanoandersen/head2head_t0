from django.contrib.auth import authenticate
from django.shortcuts import render
from datetime import datetime;
from .models import Profile, League, Team, Draft, Notification
from all_players.models import Player  # Import the Player model from the all_players app
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, permissions
import logging
from .serializers import UserSerializer, ProfileSerializer, LeagueSerializer, TeamSerializer, NotificationSerializer
import random
from django.core.paginator import Paginator
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_unread(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = False
        notification.save()
        return Response({'success': 'Notification marked as unread.'}, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)


def notify_draft_start(league):
    """Notify all users in the league that the draft has started."""
    channel_layer = get_channel_layer()
    for user in league.users.all():
        # Create a notification in the database
        notification = Notification.objects.create(
            user=user,
            message=f"The draft for {league.name} has started!",
            link=f"/draft/{league.id}/"
        )

        # Send the notification via WebSocket
        async_to_sync(channel_layer.group_send)(
            f"notifications_{user.id}",
            {
                "type": "send_notification",
                "message": {
                    "id": notification.id,
                    "message": notification.message,
                    "link": notification.link,
                    "is_read": notification.is_read,
                    "created_at": str(notification.created_at),
                },
            },
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    limit = request.query_params.get('limit', None)  # Optional query parameter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    if limit:
        notifications = notifications[:int(limit)]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'success': 'Notification marked as read.'}, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return Response({'success': 'Notification deleted.'}, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_league(request, league_id):
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response({"error": "League not found"}, status=status.HTTP_404_NOT_FOUND)

    if league.draftStarted:
        return Response({"error": "Cannot leave a league after the draft has started."}, status=status.HTTP_400_BAD_REQUEST)

    if request.user == league.owner:
        return Response({"error": "Owners cannot leave their own league. They must delete it instead."}, status=status.HTTP_400_BAD_REQUEST)

    if request.user not in league.users.all():
        return Response({"error": "You are not a member of this league."}, status=status.HTTP_403_FORBIDDEN)

    league.users.remove(request.user)
    return Response({"message": "Successfully left the league."}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_league(request, league_id):
    logger.info(f"Received request to delete league with ID: {league_id} by user: {request.user.username}")

    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        logger.error(f"League with ID {league_id} not found.")
        return Response({"error": "League not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user != league.owner:
        logger.error(f"User {request.user.username} is not the owner of league {league_id}.")
        return Response({"error": "Only the owner can delete this league."}, status=status.HTTP_403_FORBIDDEN)

    if league.draftStarted:
        logger.error(f"Cannot delete league {league_id} because the draft has started.")
        return Response({"error": "Cannot delete a league after the draft has started."}, status=status.HTTP_400_BAD_REQUEST)

    league.delete()
    logger.info(f"League with ID {league_id} successfully deleted.")
    return Response({"message": "League successfully deleted."}, status=status.HTTP_200_OK)


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


    # Notify all users about the draft start
    notify_draft_start(league)

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
    return Response({
        'draftStarted': league.draftStarted,
        'draftComplete': league.draftComplete,  # Include draftComplete in the response
        'currentPickUser': current_pick_user
    }, status=status.HTTP_200_OK)

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



@api_view(['GET'])
@permission_classes([AllowAny])
def search_league(request):
    name_query = request.GET.get("name", "").strip()  # Search by name
    is_private = request.GET.get("private", None)  # Filter by private/public
    positional_betting = request.GET.get("positional_betting", None)  # Filter by positional betting
    draft_status = request.GET.get("draft_status", None)  # Filter by draft status
    draft_date = request.GET.get("draft_date", None)  # Filter by draft date (before/after)
    page = int(request.GET.get("page", 1))  # Pagination
    leagues_per_page = 10  # Leagues per page

    leagues = League.objects.all()

    # Debugging: Print initial query
    print(f"Initial leagues query: {leagues}")

    # Apply filters
    if name_query:
        leagues = leagues.filter(name__icontains=name_query)
        print(f"Filtered by name: {name_query}")

    if is_private is not None and is_private != "":
        if is_private == "1":
            leagues = leagues.filter(private=True)
        elif is_private == "0":
            leagues = leagues.filter(private=False)
        print(f"Filtered by private: {is_private}")
    else:
        print("No filtering applied for private/public.")

    if positional_betting is not None and positional_betting != "":
        if positional_betting == "1":
            leagues = leagues.filter(positional_betting=True)
        elif positional_betting == "0":
            leagues = leagues.filter(positional_betting=False)
        print(f"Filtered by positional_betting: {positional_betting}")
    else:
        print("No filtering applied for positional_betting.")

    if draft_status is not None and draft_status != "":
        if draft_status == "0":  # Not Started
            leagues = leagues.filter(draftStarted=False, draftComplete=False)
        elif draft_status == "1":  # In Progress
            leagues = leagues.filter(draftStarted=True, draftComplete=False)
        elif draft_status == "2":  # Completed
            leagues = leagues.filter(draftComplete=True)
        print(f"Filtered by draft_status: {draft_status}")
    else:
        print("No filtering applied for draft_status.")

    if draft_date:
        try:
            date_filter = datetime.strptime(draft_date, "%Y-%m-%d")
            leagues = leagues.filter(draft_date__gte=date_filter)  # Filter leagues after the given date
            print(f"Filtered by draft_date: {draft_date}")
        except ValueError:
            print(f"Invalid draft_date format: {draft_date}")
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    # Debugging: Print final query
    print(f"Final leagues query: {leagues}")

    # Paginate results
    paginator = Paginator(leagues, leagues_per_page)
    try:
        paginated_leagues = paginator.get_page(page)
    except Exception as e:
        print(f"Pagination error: {str(e)}")
        return JsonResponse({"error": "Invalid page number."}, status=400)

    league_data = [
        {
            "id": league.id,
            "name": league.name,
            "owner": league.owner.username,
            "draft_date": league.draft_date,
            "private": league.private,
            "positional_betting": league.positional_betting,
            "draftStarted": league.draftStarted,
            "draftComplete": league.draftComplete,
        }
        for league in paginated_leagues
    ]

    return JsonResponse({
        "results": league_data,
        "totalPages": paginator.num_pages
    })


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