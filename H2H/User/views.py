from django.contrib.auth import authenticate
from django.shortcuts import render

from .models import Profile, League, Team
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
from .serializers import UserSerializer, ProfileSerializer, LeagueSerializer, TeamSerializer

logger = logging.getLogger(__name__)






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