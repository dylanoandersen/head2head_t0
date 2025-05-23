import json

from django.contrib.auth import authenticate
from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import render
from datetime import datetime;
from django.db import models  # Import models to fix "models is not defined"
from decimal import Decimal
import re
from django.views.decorators.csrf import csrf_exempt

from all_players.models import Player, Player_Stats

from .models import Profile, League, Team, Draft, Notification, Invite, Matchup, Bet, Week, TradeRequest

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
def get_users_and_teams(request, league_id):
    try:
        league = League.objects.get(id=league_id)

        users = league.users.all()

        data = []
        for user in users:
            try:
                team = Team.objects.get(league=league, author=user)
                team_data = {
                    "team_title": team.title,
                    "players": {
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
                    },
                }
            except Team.DoesNotExist:
                team_data = None

            data.append({
                "user_id": user.id,
                "username": user.username,
                "team": team_data,
            })

        return Response(data, status=status.HTTP_200_OK)

    except League.DoesNotExist:
        return Response({"error": "League not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trade_requests(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        user_team = Team.objects.get(league=league, author=request.user)

        trade_requests = TradeRequest.objects.filter(receiver_team=user_team)

        player_ids = set()
        for tr in trade_requests:
            for value in tr.sender_players.values():
                if isinstance(value, list):
                    player_ids.update(value)
                else:
                    player_ids.add(value)
            for value in tr.receiver_players.values():
                if isinstance(value, list):
                    player_ids.update(value)
                else:
                    player_ids.add(value)

        players = Player.objects.filter(id__in=player_ids)
        player_map = {
            str(player.id): {
                "name": f"{player.firstName} {player.lastName}",
                "position": player.position
            }
            for player in players
        }

        trade_requests_data = [
            {
                "id": tr.id,
                "sender_team": {
                    "title": tr.sender_team.title,
                    "author": {"username": tr.sender_team.author.username},
                },
                "receiver_team": {"title": tr.receiver_team.title},
                "sender_players": {
                    pos: {
                        "id": pid,
                        "name": player_map.get(str(pid), {}).get("name", "Unknown"),
                        "position": player_map.get(str(pid), {}).get("position", "Unknown"),
                    }
                    for pos, pid in tr.sender_players.items()
                },
                "receiver_players": {
                    pos: {
                        "id": pid,
                        "name": player_map.get(str(pid), {}).get("name", "Unknown"),
                        "position": player_map.get(str(pid), {}).get("position", "Unknown"),
                    }
                    for pos, pid in tr.receiver_players.items()
                },
                "currency_offered": tr.currency_offered,
                "currency_requested": tr.currency_requested,
                "status": tr.status,
                "created_at": tr.created_at,
            }
            for tr in trade_requests
        ]

        return Response(trade_requests_data, status=status.HTTP_200_OK)

    except League.DoesNotExist:
        return Response({"error": "League not found."}, status=status.HTTP_404_NOT_FOUND)
    except Team.DoesNotExist:
        return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"Internal server error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_trade_request(request, trade_request_id):
    try:
        trade_request = TradeRequest.objects.get(id=trade_request_id)
        if request.user != trade_request.receiver_team.author:
            return Response({"error": "You are not authorized to respond to this trade request."}, status=status.HTTP_403_FORBIDDEN)

        response = request.data.get("response")
        if response == "accept":
            # Validate positions
            sender_positions = list(trade_request.sender_players.keys())
            receiver_positions = list(trade_request.receiver_players.keys())

            if len(sender_positions) != 1 or len(receiver_positions) != 1:
                return Response({"error": "Invalid trade request. Only one player per position can be traded."}, status=status.HTTP_400_BAD_REQUEST)

            sender_position = sender_positions[0]
            receiver_position = receiver_positions[0]

            # Allow trades between WR1 and WR2, RB1 and RB2, and Bench players
            valid_trades = {
                "WR1": ["WR2", "WR1"],
                "WR2": ["WR1", "WR2"],
                "RB1": ["RB2", "RB1"],
                "RB2": ["RB1", "RB2"],
                "BN1": ["BN2", "BN3", "BN4", "BN5", "BN6"],
                "BN2": ["BN1", "BN3", "BN4", "BN5", "BN6"],
                "BN3": ["BN1", "BN2", "BN4", "BN5", "BN6"],
                "BN4": ["BN1", "BN2", "BN3", "BN5", "BN6"],
                "BN5": ["BN1", "BN2", "BN3", "BN4", "BN6"],
                "BN6": ["BN1", "BN2", "BN3", "BN4", "BN5"],
                "TE": ["TE"],
                "QB": ["QB"],
                "K": ["K"],
                "DEF": ["DEF"],
                "FLX": ["FLX"],
            }

            if sender_position != receiver_position and receiver_position not in valid_trades.get(sender_position, []):
                return Response({"error": "Players must be of the same position or valid interchangeable positions to trade."}, status=status.HTTP_400_BAD_REQUEST)

            # Verify player ownership
            sender_team = trade_request.sender_team
            receiver_team = trade_request.receiver_team
            sender_player_id = list(trade_request.sender_players.values())[0]
            receiver_player_id = list(trade_request.receiver_players.values())[0]

            if not any(getattr(sender_team, field.name) == sender_player_id for field in sender_team._meta.fields if field.name.startswith(("QB", "RB", "WR", "BN"))):
                return Response({"error": "Sender no longer owns the player being traded."}, status=status.HTTP_400_BAD_REQUEST)

            if not any(getattr(receiver_team, field.name) == receiver_player_id for field in receiver_team._meta.fields if field.name.startswith(("QB", "RB", "WR", "BN"))):
                return Response({"error": "Receiver no longer owns the player being traded."}, status=status.HTTP_400_BAD_REQUEST)

            # Execute the trade
            process_trade(
                trade_request.sender_team,
                trade_request.receiver_team,
                trade_request.sender_players,
                trade_request.receiver_players,
                trade_request.currency_offered,
                trade_request.currency_requested,
            )
            trade_request.status = "accepted"
            trade_request.save()

            # Notify the sender
            Notification.objects.create(
                user=trade_request.sender_team.author,
                message="Your trade request has been accepted.",
            )

        elif response == "reject":
            trade_request.status = "rejected"
            trade_request.save()

            # Notify the sender
            Notification.objects.create(
                user=trade_request.sender_team.author,
                message="Your trade request has been rejected.",
            )

        return Response({"success": f"Trade request {response}ed successfully."}, status=status.HTTP_200_OK)

    except TradeRequest.DoesNotExist:
        return Response({"error": "Trade request not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_trade_request(request, league_id):
    try:
        league = League.objects.get(id=league_id)
        sender_team = Team.objects.get(league=league, author=request.user)
        receiver_team_id = request.data.get("receiver_team_id")
        receiver_team = Team.objects.get(id=receiver_team_id, league=league)

        sender_players = request.data.get("sender_players", {})
        receiver_players = request.data.get("receiver_players", {})
        currency_offered = Decimal(request.data.get("currency_offered", 0))
        currency_requested = Decimal(request.data.get("currency_requested", 0))

      

        # Validate positions
        sender_positions = list(sender_players.keys())
        receiver_positions = list(receiver_players.keys())
        if len(sender_positions) != 1 or len(receiver_positions) != 1:
            return Response({"error": "You must select exactly one player from each team."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        sender_position = sender_positions[0]
        receiver_position = receiver_positions[0]


        # Allow trades between WR1 and WR2, RB1 and RB2, and Bench players
        valid_trades = {
            "WR1": ["WR2", "WR1"],
            "WR2": ["WR1", "WR2"],
            "RB1": ["RB2", "RB1"],
            "RB2": ["RB1", "RB2"],
            "BN1": ["BN2", "BN3", "BN4", "BN5", "BN6"],
            "BN2": ["BN1", "BN3", "BN4", "BN5", "BN6"],
            "BN3": ["BN1", "BN2", "BN4", "BN5", "BN6"],
            "BN4": ["BN1", "BN2", "BN3", "BN5", "BN6"],
            "BN5": ["BN1", "BN2", "BN3", "BN4", "BN6"],
            "BN6": ["BN1", "BN2", "BN3", "BN4", "BN5"],
            "TE": ["TE"],
            "QB": ["QB"],
            "K": ["K"],
            "DEF": ["DEF"],
            "FLX": ["FLX"],
        }


        
        print(f"Sender Position: {sender_position}, Receiver Position: {receiver_position}")
        print(f"Valid Trades for {sender_position}: {valid_trades.get(sender_position, [])}")
        

        # Check if positions are valid for trade
        if sender_position != receiver_position and receiver_position not in valid_trades.get(sender_position, []):
            return Response({"error": "Players must be of the same position or valid interchangeable positions to trade."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the trade request
        trade_request = TradeRequest.objects.create(
            league=league,
            sender_team=sender_team,
            receiver_team=receiver_team,
            sender_players=sender_players,
            receiver_players=receiver_players,
            currency_offered=currency_offered,
            currency_requested=currency_requested,
        )

        # Notify the receiver
        Notification.objects.create(
            user=receiver_team.author,
            message="You have received a trade request.",
            link=f"/leagues/{league_id}/trade-requests/"
        )

        return Response({"success": "Trade request created successfully."}, status=status.HTTP_201_CREATED)

    except League.DoesNotExist:
        return Response({"error": "League not found."}, status=status.HTTP_404_NOT_FOUND)
    except Team.DoesNotExist:
        return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
    try:
        matchup = Matchup.objects.get(id=matchup_id)

        user_team = Team.objects.get(league=matchup.league, author=request.user)
        opponent_team = (
            Team.objects.get(league=matchup.league, author_id=matchup.team1_id)
            if matchup.team2_id == request.user.id
            else Team.objects.get(league=matchup.league, author_id=matchup.team2_id)
        )

        position_map = {
            "QB": ["QB"],
            "RB": ["RB1", "RB2"],
            "WR": ["WR1", "WR2"],
            "TE": ["TE"],
            "FLX": ["FLX"],
            "K": ["K"],
            "DEF": ["DEF"],
        }

        relevant_fields = position_map.get(matchup.position, [])

        user_players = []
        for pos in relevant_fields:
            player_id = getattr(user_team, pos, None)
            if player_id:
                try:
                    player = Player.objects.get(id=player_id)
                    user_players.append({
                        "id": player.id,
                        "name": f"{player.firstName} {player.lastName}", 
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
                        "name": f"{player.firstName} {player.lastName}",
                        "position": pos,
                    })
                except Player.DoesNotExist:
                    continue

        return Response({
            "user_players": user_players,
            "opponent_players": opponent_players,
        }, status=status.HTTP_200_OK)

    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
    except Team.DoesNotExist:
        return Response({"error": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"[ERROR] {str(e)}")
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

        player_position = request.data.get("position")
        if player_position != matchup.position:
            return Response({"error": f"Player position must match the weekly position: {matchup.position}."}, status=status.HTTP_400_BAD_REQUEST)

        if Decimal(team.author.profile.currency) < Decimal(amount):
            return Response({"error": "Insufficient currency."}, status=status.HTTP_400_BAD_REQUEST)

        if Bet.objects.filter(matchup=matchup, team=team).exists():
            return Response({"error": "You have already placed a bet for this matchup."}, status=status.HTTP_400_BAD_REQUEST)

        team.author.profile.currency = str(Decimal(team.author.profile.currency) - Decimal(amount))
        team.author.profile.save()

        Bet.objects.create(
            matchup=matchup,
            league=matchup.league,
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
        serializer = BetSerializer(bets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Home page matchup display
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_allMatchups_perUserLeague(request):
    try:
        lst = []
        print('user:', request.user)
        leagues = League.objects.filter(users=request.user)
        for league in leagues:
            print('league:', league.id)
            lst.append(league.id)
        matchups = Matchup.objects.filter(league_id__in=lst)
        print(matchups)

        serializer = MatchupSerializer(matchups, many=True)
        return Response(serializer.data)

    except Matchup.DoesNotExist:
        return Response({"error": "Matchup not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_matchup(request, league_id):
    try:
        logger.debug(f"Fetching matchup for league_id={league_id}, user_id={request.user.id}")
        current_week = Week.objects.first().week if Week.objects.exists() else 1
        logger.debug(f"Current week: {current_week}")

        queryset = Matchup.objects.filter(
            league_id=league_id,
            week=current_week,
        ).filter(
            models.Q(team1_id=request.user.id) | models.Q(team2_id=request.user.id)
        )
        logger.debug(f"Queryset: {queryset.query}")
        matchup = queryset.first()

        if not matchup:
            logger.warning(f"No matchup found for user_id={request.user.id} in league_id={league_id}")
            return Response({
                "error": "No matchup found for the current user.",
                "league_id": league_id,
                "user_id": request.user.id,
                "current_week": current_week,
            }, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Matchup found: {matchup.id}")
        return Response({"matchupId": matchup.id}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_user_matchup: {str(e)}")
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
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_eligible_leagues(request, user_id):
    try:
        searched_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    owned_leagues = request.user.owned_leagues.filter(draftStarted=False)

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

    if Invite.objects.filter(league=league, invited_user=user).exists():
        return Response({"error": "This user has already been invited to this league."}, status=status.HTTP_400_BAD_REQUEST)

    Invite.objects.create(league=league, invited_user=user, invited_by=request.user)

    Notification.objects.create(
        user=user,
        message=f"You have been invited to join the league '{league.name}'.",
        link=f"/api/leagues/{league_id}/invite-response/"
    )

    return Response({"success": f"User {user.username} has been invited to the league."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.query_params.get("username", "").strip()
    if not query:
        return Response({"error": "Username query is required."}, status=status.HTTP_400_BAD_REQUEST)

    users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
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
            print(f"Notification created for user {user.username}: The draft for {league.name} has started!")
        except Exception as e:
            logger.error(f"Failed to create notification for user {user.username}: {e}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    limit = request.query_params.get('limit', None)
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
    try:
        league = League.objects.get(id=league_id, owner=request.user)
    except League.DoesNotExist:
        return Response({'error': 'League not found or you are not the owner.'}, status=403)

    data = request.data

    # Validate join code if the league is private
    if data.get('private') and ('join_code' not in data or not re.match(r'^[a-zA-Z0-9]{1,6}$', data['join_code'])):
        return Response({'error': 'Join code must be 1-6 alphanumeric characters.'}, status=400)

    # Update fields
    for field in ['max_capacity', 'private', 'join_code']:
        if field in data:
            setattr(league, field, data[field])

    league.save()
    return Response({'success': 'League settings updated successfully.'})


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
            # Extract and validate token
            token = AccessToken(request.headers.get('Authorization').split()[1])
            user = request.user  # This will work if token is valid and associated with a user
            return Response({'username': user.username}, status=200)
        except TokenError as e:
            # Handle invalid or expired tokens
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
                w = Week.objects.get(id=1).week
                latest = Player_Stats.objects.get(player=currentP, week=w)
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
            league = League.objects.get(id=LID)

            teams = Team.objects.filter(league=league)

            if not teams.exists():
                return Response({"error": "No teams found in this league."}, status=status.HTTP_404_NOT_FOUND)
        except League.DoesNotExist:
            return Response({"error": f"League with ID {LID} does not exist."}, status=status.HTTP_404_NOT_FOUND)

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
    w = Week.objects.get(id=1).week
    weekly = Matchup.objects.filter(week = w)
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
                    w = Week.objects.get(id=1).week
                    stats = Player_Stats.objects.get(player=player, week = w)
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
    name_query = request.GET.get("name", "").strip() 
    is_private = request.GET.get("private", None)
    positional_betting = request.GET.get("positional_betting", None)
    draft_status = request.GET.get("draft_status", None)
    draft_date = request.GET.get("draft_date", None)
    page = int(request.GET.get("page", 1))
    leagues_per_page = 10

    leagues = League.objects.all()

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
            leagues = leagues.filter(draft_date__gte=date_filter)
            print(f"Filtered by draft_date: {draft_date}")
        except ValueError:
            print(f"Invalid draft_date format: {draft_date}")
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        
    print(f"Final leagues query: {leagues}")

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