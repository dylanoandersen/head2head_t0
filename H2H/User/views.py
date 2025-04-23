import json

from django.contrib.auth import authenticate
from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import render
from datetime import datetime;
from django.db import models  # Import models to fix "models is not defined"


from django.views.decorators.csrf import csrf_exempt

from all_players.models import Player, Player_Stats

from .models import Profile, League, Team, Draft, Notification, Invite, Matchup, Bet, Week

from .helpers import validate_trade


from rest_framework.permissions import IsAuthenticated, AllowAny
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

from .serializers import BetSerializer, UserSerializer, ProfileSerializer, LeagueSerializer, TeamSerializer, PlayerSerializer, MatchupSerializer, CustomTeamSerializer, NotificationSerializer
import random
from django.core.paginator import Paginator
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .trade_processor import process_trade

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_team_positions(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        team = Team.objects.get(league=league, author=request.user)
    except (League.DoesNotExist, Team.DoesNotExist):
        return Response({"positions": {}}, status=status.HTTP_200_OK)

    position_fields = [
        "QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLX", "K", "DEF",
        "BN1", "BN2", "BN3", "BN4", "BN5", "BN6"
    ]
    positions = {}
    for field in position_fields:
        player_id = getattr(team, field, None)
        if player_id and player_id != "N/A":
            try:
                player = Player.objects.get(id=player_id)
                positions[field] = {
                    "id": player.id,
                    "firstName": player.firstName,
                    "lastName": player.lastName,
                    "position": field,
                    "headshot": player.headshot,
                }
            except Player.DoesNotExist:
                positions[field] = None
        else:
            positions[field] = None

    return Response({"positions": positions}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_usernames(request):
    user_ids = request.data.get("user_ids", [])
    if not isinstance(user_ids, list):
        return Response({"error": "user_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)

    users = User.objects.filter(id__in=user_ids).values("id", "username")
    return Response({"usernames": {user["id"]: user["username"] for user in users}}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_user_matchup(request, league_id, matchup_id):
    try:
        matchup = Matchup.objects.get(id=matchup_id, league_id=league_id)
        if request.user.id not in [matchup.team1_id, matchup.team2_id]:
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)
        return Response({"success": "User is authorized."}, status=status.HTTP_200_OK)
    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_matchup_and_team(request, league_id, matchup_id):
    print(f"[DEBUG] User: {request.user}, Authenticated: {request.user.is_authenticated}")

    try:
        # Fetch the matchup
        print(f"[DEBUG] Fetching matchup with ID: {matchup_id} in league: {league_id}")
        matchup = Matchup.objects.get(id=matchup_id, league_id=league_id)
        print(f"[DEBUG] Matchup fetched: {matchup}")
        print(f"[DEBUG] Matchup Position: {matchup.position}")
        print(f"[DEBUG] Matchup Teams: Team1={matchup.team1_id}, Team2={matchup.team2_id}")

        # Check if the user is authorized
        if request.user.id not in [matchup.team1_id, matchup.team2_id]:
            print(f"[ERROR] Unauthorized access by user: {request.user.id}")
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch the user's team
        print(f"[DEBUG] Fetching team for user: {request.user.id} in league: {league_id}")
        team = Team.objects.get(league_id=league_id, author=request.user)
        print(f"[DEBUG] Team fetched: {team}")

        # Map positions to relevant fields in the Team model
        position_map = {
            "QB": team.QB,
            "RB1": team.RB1,
            "RB2": team.RB2,
            "WR1": team.WR1,
            "WR2": team.WR2,
            "TE": team.TE,
            "FLX": team.FLX,
            "K": team.K,
            "DEF": team.DEF,
            "BN1": team.BN1,
            "BN2": team.BN2,
            "BN3": team.BN3,
            "BN4": team.BN4,
            "BN5": team.BN5,
            "BN6": team.BN6,
            "IR1": team.IR1,
            "IR2": team.IR2,
        }
        print(f"[DEBUG] Position map: {position_map}")

        # Fetch player details
        players = []
        for pos, player_id in position_map.items():
            if player_id and player_id != "N/A":
                try:
                    player = Player.objects.get(id=player_id)
                    players.append({
                        "id": player.id,
                        "name": f"{player.firstName} {player.lastName}",
                        "position": pos,
                    })
                    print(f"[DEBUG] Player added: {player.firstName} {player.lastName} (ID: {player.id}, Position: {pos})")
                except Player.DoesNotExist:
                    print(f"[ERROR] Player with ID {player_id} does not exist for position {pos}")
                    continue

        print(f"[DEBUG] Final Players List: {players}")

        return Response({
            "weekly_position": matchup.position,
            "players": players,
        }, status=status.HTTP_200_OK)

    except Matchup.DoesNotExist:
        print("[ERROR] Matchup not found.")
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
    except Team.DoesNotExist:
        print("[ERROR] Team not found.")
        return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_players_for_betting(request, matchup_id):
    """
    Returns the user's available players and the opponent's available players for betting.
    Filters players based on the position specified in the matchup.
    """
    try:
        # Fetch the matchup
        matchup = Matchup.objects.get(id=matchup_id)

        # Fetch the user's team and the opponent's team
        user_team = Team.objects.get(league=matchup.league, author=request.user)
        opponent_team = (
            Team.objects.get(league=matchup.league, author_id=matchup.team1_id)
            if matchup.team2_id == request.user.id
            else Team.objects.get(league=matchup.league, author_id=matchup.team2_id)
        )

        # Map positions to relevant fields in the Team model
        position_map = {
            "QB": ["QB"],
            "RB": ["RB1", "RB2"],
            "WR": ["WR1", "WR2"],
            "TE": ["TE"],
            "FLX": ["FLX"],
            "K": ["K"],
            "DEF": ["DEF"],
        }

        # Get the relevant fields for the matchup position
        relevant_fields = position_map.get(matchup.position, [])

        # Fetch players for the user's team
        user_players = []
        for pos in relevant_fields:
            player_id = getattr(user_team, pos, None)
            if player_id:
                try:
                    player = Player.objects.get(id=player_id)
                    user_players.append({
                        "id": player.id,
                        "name": player.name,
                        "position": pos,
                    })
                except Player.DoesNotExist:
                    continue

        # Fetch players for the opponent's team
        opponent_players = []
        for pos in relevant_fields:
            player_id = getattr(opponent_team, pos, None)
            if player_id:
                try:
                    player = Player.objects.get(id=player_id)
                    opponent_players.append({
                        "id": player.id,
                        "name": player.name,
                        "position": pos,
                    })
                except Player.DoesNotExist:
                    continue

        return Response({
            "user_players": user_players,
            "opponent_players": opponent_players,
        }, status=status.HTTP_200_OK)

   # except Matchup.DoesNotExist:
    #    return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
   # except Team.DoesNotExist:
  #     return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"[ERROR] {str(e)}")  # Add logging
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_bet(request, league_id, matchup_id):
    try:
        matchup = Matchup.objects.get(id=matchup_id, league_id=league_id)
        if request.user.id not in [matchup.team1_id, matchup.team2_id]:
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)

        team = Team.objects.get(league_id=league_id, author=request.user)
        player_id = request.data.get("player_id")
        amount = request.data.get("amount")

        if not player_id or not amount:
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate player position
        player_position = request.data.get("position")
        if player_position != matchup.position:
            return Response({"error": f"Player position must match the weekly position: {matchup.position}."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user has enough currency
        if team.author.profile.currency < amount:
            return Response({"error": "Insufficient currency."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct currency and create the bet
        team.author.profile.currency -= amount
        team.author.profile.save()

        Bet.objects.create(
            matchup=matchup,
            league_id=league_id,
            team=team,
            player_id=player_id,
            position=matchup.position,
            amount=amount
        )
        return Response({"success": "Bet placed successfully."}, status=status.HTTP_201_CREATED)
    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
    except Team.DoesNotExist:
        return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bets_for_matchup(request, matchup_id):
    try:
        matchup = Matchup.objects.get(id=matchup_id)
        bets = Bet.objects.filter(matchup=matchup)
        serializer = BetSerializer(bets, many=True)  # Ensure you have a `BetSerializer`
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_matchup(request, league_id):
    try:
        current_week = Week.objects.first().week
        matchup = Matchup.objects.filter(
            league_id=league_id,
            week=current_week
        ).filter(
            models.Q(team1_id=request.user.id) | models.Q(team2_id=request.user.id)
        ).first()
        print(f"League ID: {league_id}, Current Week: {current_week}, User ID: {request.user.id}")
        print(f"Matchup Query Result: {matchup}")

        if not matchup:
            return Response({"error": "No matchup found for the current user."}, status=status.HTTP_404_NOT_FOUND)


        return Response({"matchupId": matchup.id}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_matchup(request, matchup_id):
    try:
        matchup = Matchup.objects.get(id=matchup_id)
        serializer = MatchupSerializer(matchup)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_bet(request, matchup_id):
    try:
        matchup = Matchup.objects.get(id=matchup_id)
        league = matchup.league
        team = Team.objects.get(league=league, author=request.user)
        player_id = request.data.get("player_id")
        amount = request.data.get("amount")

        if not player_id or not amount:
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the player belongs to the user's team
        if not any(player_id == getattr(team, pos) for pos in ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLX", "K", "DEF", "BN1", "BN2", "BN3", "BN4", "BN5", "BN6", "IR1", "IR2"]):
            return Response({"error": "Player does not belong to your team."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the position matches the matchup's position
        player_position = request.data.get("position")
        if player_position != matchup.position:
            return Response({"error": f"Player position must match the weekly position: {matchup.position}."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user has enough currency
        if team.author.profile.currency < amount:
            return Response({"error": "Insufficient currency."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user hasn't already placed a bet
        if Bet.objects.filter(matchup=matchup, team=team).exists():
            return Response({"error": "You have already placed a bet for this matchup."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct currency and create the bet
        team.author.profile.currency -= amount
        team.author.profile.save()

        Bet.objects.create(
            matchup=matchup,
            league=league,
            team=team,
            player_id=player_id,
            position=matchup.position,
            amount=amount
        )
        return Response({"success": "Bet placed successfully."}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_eligible_leagues(request, user_id):
    try:
        searched_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Fetch leagues owned by the logged-in user
    owned_leagues = request.user.owned_leagues.filter(draftStarted=False)

    # Exclude leagues where the searched user is already a member
    eligible_leagues = owned_leagues.exclude(users=searched_user)

    serializer = LeagueSerializer(eligible_leagues, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_leagues(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Get leagues the user owns or has joined
    owned_leagues = user.owned_leagues.all()
    joined_leagues = user.joined_leagues.all()

    # Combine and serialize the leagues
    leagues = owned_leagues | joined_leagues
    serializer = LeagueSerializer(leagues, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_invite_response(request, league_id, user_response):
    print(f"DEBUG: Received request - league_id={league_id}, user_response={user_response}, user={request.user}")

    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        print(f"DEBUG: League with id {league_id} does not exist.")
        return Response({"error": "League not found."}, status=status.HTTP_404_NOT_FOUND)

    if user_response not in ["accept", "decline"]:
        print(f"DEBUG: Invalid user response - {user_response}")
        return Response({"error": "Invalid response."}, status=status.HTTP_400_BAD_REQUEST)

    invite = Invite.objects.filter(league=league, invited_user=request.user).first()
    if not invite:
        print(f"DEBUG: No invite found for user {request.user} in league {league_id}")
        return Response({"error": "No invite found for this league."}, status=status.HTTP_404_NOT_FOUND)

    if user_response == "accept":
        if request.user in league.users.all():
            print(f"DEBUG: User {request.user} is already a member of the league.")
            return Response({"error": "You are already a member of this league."}, status=status.HTTP_400_BAD_REQUEST)

        if league.users.count() >= league.max_capacity:
            print(f"DEBUG: League {league_id} is full.")
            return Response({"error": "This league is full."}, status=status.HTTP_400_BAD_REQUEST)

        league.users.add(request.user)
        invite.delete()
        print(f"DEBUG: User {request.user} successfully joined league {league_id}.")
        return Response({"success": f"You have successfully joined the league '{league.name}'."}, status=status.HTTP_200_OK)

    invite.delete()
    print(f"DEBUG: User {request.user} declined the invite for league {league_id}.")
    return Response({"success": "You have declined the league invitation."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_user_to_league(request, league_id, user_id):
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response({"error": "League not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.user != league.owner:
        return Response({"error": "Only the league owner can invite users."}, status=status.HTTP_403_FORBIDDEN)

    if league.draftStarted:
        return Response({"error": "Cannot invite users after the draft has started."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check if an invite already exists
    if Invite.objects.filter(league=league, invited_user=user).exists():
        return Response({"error": "This user has already been invited to this league."}, status=status.HTTP_400_BAD_REQUEST)

    # Create an invite record
    Invite.objects.create(league=league, invited_user=user, invited_by=request.user)

    # Create a notification for the invited user
    Notification.objects.create(
        user=user,
        message=f"You have been invited to join the league '{league.name}'.",
        link=f"/api/leagues/{league_id}/invite-response/"  # Add a valid link
    )

    return Response({"success": f"User {user.username} has been invited to the league."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.query_params.get("username", "").strip()
    if not query:
        return Response({"error": "Username query is required."}, status=status.HTTP_400_BAD_REQUEST)

    users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)  # Exclude the logged-in user
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

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
    for user in league.users.all():
        try:
            # Create a notification in the database
            Notification.objects.create(
                user=user,
                message=f"The draft for {league.name} has started!",
                link=f"/draft/{league.id}/"
            )
            print(f"Notification created for user {user.username}: The draft for {league.name} has started!")  # Debugging log
        except Exception as e:
            logger.error(f"Failed to create notification for user {user.username}: {e}")

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
        return Response({"error": "League or draft not found."}, status=status.HTTP_404_NOT_FOUND)

    # Enrich draft picks with player names
    enriched_picks = []
    for pick in draft.picks:
        try:
            player = Player.objects.get(id=pick['player_id'])
            enriched_picks.append({
                "user_id": pick['user_id'],
                "player_name": f"{player.firstName} {player.lastName}",
                "position": pick['position']
            })
        except Player.DoesNotExist:
            enriched_picks.append({
                "user_id": pick['user_id'],
                "player_name": "Unknown Player",
                "position": pick['position']
            })

    return Response({"picks": enriched_picks}, status=status.HTTP_200_OK)

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
    player_parms = request.GET.get('players', None)
    player_list = player_parms.split(',') if player_parms else []
    print(f"Player List: {player_list}")

    for id in player_list:
        if id in [None, "null", "N/A", ""]:
            # Create a placeholder "empty" player object (not saved to the DB)
            empty_player = Player(
                id=None,
                firstName="Empty",
                lastName="",
                status="x",
                position="",
                team="",
            )
            setattr(empty_player, 'proj_fantasy', 0)
            setattr(empty_player, 'total_fantasy_points', 0)
            setattr(empty_player, 'pass_yards', 0)
            setattr(empty_player, 'pass_tds', 0)
            setattr(empty_player, 'receiving_yards', 0)
            setattr(empty_player, 'receiving_tds', 0)
            setattr(empty_player, 'rush_yards', 0)
            setattr(empty_player, 'rush_tds', 0)
            setattr(empty_player, 'fg_made', 0)
            setattr(empty_player, 'extra_points_made', 0)
            objectList.append(empty_player)
            continue


        try:
            currentP = Player.objects.get(id=id)
            try:
                latest = Player_Stats.objects.get(player=currentP, week=1)
                setattr(currentP, 'proj_fantasy', latest.proj_fantasy)  # Attach to Player object
                setattr(currentP, 'total_fantasy_points', latest.total_fantasy_points)  # Attach to Player object
                setattr(currentP, 'pass_yards', latest.pass_yards)
                setattr(currentP, 'pass_tds', latest.pass_tds)
                setattr(currentP, 'receiving_yards', latest.receiving_yards)
                setattr(currentP, 'receiving_tds', latest.receiving_tds)
                setattr(currentP, 'rush_yards', latest.rush_yards)
                setattr(currentP, 'rush_tds', latest.rush_tds)
                setattr(currentP, 'fg_made', latest.fg_made)
                setattr(currentP, 'extra_points_made', latest.extra_points_made)
            except Player_Stats.DoesNotExist:
                print(f"No stats found for player {currentP.id}")
                setattr(currentP, 'proj_fantasy', 0)
                setattr(currentP, 'total_fantasy_points', 0)
                setattr(currentP, 'pass_yards', 0)
                setattr(currentP, 'pass_tds', 0)
                setattr(currentP, 'receiving_yards', 0)
                setattr(currentP, 'receiving_tds', 0)
                setattr(currentP, 'rush_yards', 0)
                setattr(currentP, 'rush_tds', 0)
                setattr(currentP, 'fg_made', 0)
                setattr(currentP, 'extra_points_made', 0)


            objectList.append(currentP)
        except Player.DoesNotExist:
            print(f"Player with ID {id} does not exist.")
            # Optionally, add a placeholder for missing players
            empty_player = Player(
                id=None,
                firstName="Missing",
                lastName="Player",
                status="x",
                position="",
                team="",
            )
            setattr(empty_player, 'proj_fantasy', 0)
            setattr(empty_player, 'total_fantasy_points', 0)
            objectList.append(empty_player)

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
def TradeInfo(request, LID):
    if request.method == 'GET':
        try:
            # Fetch the league by ID
            league = League.objects.get(id=LID)

            # Fetch all teams associated with the league
            teams = Team.objects.filter(league=league)

            # Check if there are teams in the league
            if not teams.exists():
                return Response({"error": "No teams found in this league."}, status=status.HTTP_404_NOT_FOUND)
        except League.DoesNotExist:
            return Response({"error": f"League with ID {LID} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the teams and return their data
        serializer = TeamSerializer(teams, many=True)
        return Response({
            "league": league.name,
            "teams": serializer.data,
        })
    else:
        return Response({"error": "Invalid request method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leagueMatchups(request):
    members = request.GET.get("members", "")
    member_ids = [int(x) for x in members.split(",") if x.strip()]
    weekly = Matchup.objects.filter(week = 1)
    matchups = []
    for m in weekly:
        if m.team1.id in member_ids and m.team2.id in member_ids:
            matchups.append(m)

    serializer = MatchupSerializer(matchups, many = True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def allTeams(request):
    members = request.GET.get("members")
    league = request.GET.get("leagueID")
    bool = request.GET.get("matchup")
    member_ids = [int(x) for x in members.split(",") if x.strip()]
    leagueid = int(league)

    league = League.objects.get(id=leagueid)
    teamLst = []
    # List of position fields in Team
    position_fields = [
        'QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLX', 'K', 'DEF',
        'BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2'
    ]
    for user_id in member_ids:
        if user_id == request.user.id and bool == "true":
            continue
        author = User.objects.get(id=user_id)
        team = Team.objects.get(league=league, author=author)
        team_data = {
            'id': team.id,
            'title': team.title,
            'rank': team.rank,
            'author': team.author.username,
            'wins': team.wins,
            'losses': team.losses,
            'points_for': team.points_for,
            'points_against': team.points_against,
        }

        for pos in position_fields:
            player_id = getattr(team, pos)
            if player_id and player_id != "N/A" and player_id != "" and player_id != "null":
                player = Player.objects.get(id = player_id)
                fullName = player.firstName + " " + player.lastName

                try:
                    stats = Player_Stats.objects.get(player=player, week = 1) # get most recent
                    team_data[pos] = {
                        'id': player_id,
                        'fullName': fullName,
                        'proj_fantasy': stats.proj_fantasy,
                        'total_fantasy_points': stats.total_fantasy_points
                    }
                except:
                    team_data[pos] = {
                        'id': player_id,
                        'fullName': fullName,
                        'proj_fantasy': None,
                        'total_fantasy_points': None
                    }
            else:
                team_data[pos] = None
        teamLst.append(team_data)
    serializer = CustomTeamSerializer(teamLst, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def saveUserTeam(request):
    data = request.data  # Get JSON payload
    team_data = data.get('team')
    team_id = team_data.get('id')  # Check if an ID exists

    try:
        team = Team.objects.get(id=team_id, author=request.user)
        serializer = TeamSerializer(team, data=team_data, partial=True)  # Partial update
        action = "updated"

        print('checking serializer')
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"Team {action} successfully!", "team": serializer.data}, status=status.HTTP_200_OK)
        if not serializer.is_valid():
            print("❌ Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Team.DoesNotExist:
        return Response({"error": "Team not found"}, status=status.HTTP_404_NOT_FOUND)
    except League.DoesNotExist:
        return Response({"error": "League not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_trade(request, League_id):
    try:
        body = request.data
        user_players = body.get("userPlayers", {})
        opponent_players = body.get("opponentPlayers", {})
        opponent_team_id = body.get("opponentTeamId")
        currency_offered = body.get("currencyOffered", 0)
        currency_requested = body.get("currencyRequested", 0)

        # Validate league and teams
        league = League.objects.get(id=League_id)
        user_team = Team.objects.get(league=league, author=request.user)
        opponent_team = Team.objects.get(id=opponent_team_id, league=league)

        # Validate trade
        if not validate_trade(user_team, opponent_team, user_players, opponent_players, currency_offered, currency_requested):
            return Response({"error": "Invalid trade. Ensure positional equivalence, valid players, and sufficient funds."}, status=400)

        # Process trade in a transaction
        with transaction.atomic():
            process_trade(user_team, opponent_team, user_players, opponent_players, currency_offered, currency_requested)

        return Response({"message": "Trade executed successfully!"}, status=200)
    except League.DoesNotExist:
        return Response({"error": "League not found."}, status=404)
    except Team.DoesNotExist:
        return Response({"error": "User or opponent team not found in this league."}, status=404)
    except Exception as e:
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)