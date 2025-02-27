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